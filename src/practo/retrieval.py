"""Tasks 2–5,16: real local embeddings, two Chroma collections and extractive RAG."""
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
import os
import re

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from .guardrails import FALLBACK, normalize

ROOT = Path(__file__).resolve().parents[2]
# Editable installation is intended; project documents live beside pyproject.toml.
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
STRATEGIES = ("fixed", "sentence")
CALIBRATION_IN = ["How do I book an appointment?", "What is the cancellation and rescheduling window?", "What is the turnaround time for laboratory blood test results?"]
CALIBRATION_OUT = ["How do I repair a bicycle chain?", "Who won the football world cup in 1998?"]


@dataclass(frozen=True)
class Document:
    document_id: str
    title: str
    text: str


def load_documents(directory):
    docs = []
    for path in sorted(Path(directory).glob("*.md")):
        content = re.sub(r"<!--.*?-->", "", path.read_text(), flags=re.S).strip()
        title, text = content.split("\n", 1)
        docs.append(Document(path.stem, title.lstrip("# "), text.strip()))
    return docs


def sentences(text):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if x.strip()]


def chunk_document(doc, strategy):
    if strategy == "fixed":
        words = doc.text.split()
        chunks = [" ".join(words[i:i+48]) for i in range(0, len(words), 36)]
    elif strategy == "sentence":
        parts = sentences(doc.text)
        chunks = [" ".join(parts[i:i+2]) for i in range(max(1, len(parts)-1))]
    else:
        raise ValueError("Unknown chunking strategy")
    return [{"id": f"{doc.document_id}-{i}", "text": c,
             "document_id": doc.document_id, "title": doc.title} for i,c in enumerate(chunks)]


class RagCore:
    def __init__(self, model_path=None, documents_dir=None):
        self.lock = RLock()
        self.model_path = Path(model_path or os.getenv("EMBEDDING_MODEL_PATH", str(ROOT / "models/all-MiniLM-L6-v2")))
        if not self.model_path.is_dir():
            raise FileNotFoundError("Local embedding model missing. Run python scripts/download_model.py once during setup.")
        self.model = SentenceTransformer(str(self.model_path), local_files_only=True, device="cpu")
        self.documents = {d.document_id:d for d in load_documents(documents_dir or ROOT / "knowledge_base")}
        self.client = chromadb.EphemeralClient(Settings(anonymized_telemetry=False))
        # Each instance uses isolated collections; namespace is non-semantic and not evidence.
        import uuid
        namespace = uuid.uuid4().hex[:8]
        self.collections = {s:self.client.create_collection(f"practo_{s}_{namespace}",
                            metadata={"hnsw:space":"cosine"}, embedding_function=None) for s in STRATEGIES}
        self.revision = 0
        self.cache = {}
        self.generation_calls = 0
        self.retrieval_calls = 0
        self.strategy = "sentence"
        for s in STRATEGIES:
            self._index(list(self.documents.values()), s)
        self.calibration = {s:self.calibrate(s) for s in STRATEGIES}

    def _index(self, docs, strategy):
        chunks = [c for doc in docs for c in chunk_document(doc, strategy)]
        embeddings = self.model.encode([c["text"] for c in chunks], normalize_embeddings=True).tolist()
        self.collections[strategy].upsert(ids=[c["id"] for c in chunks],
            documents=[c["text"] for c in chunks], embeddings=embeddings,
            metadatas=[{"document_id":c["document_id"], "title":c["title"]} for c in chunks])

    def retrieve(self, query, strategy=None, k=4):
        with self.lock:
            self.retrieval_calls += 1
            collection = self.collections[strategy or self.strategy]
            result = collection.query(query_embeddings=self.model.encode([query], normalize_embeddings=True).tolist(),
                n_results=min(k, collection.count()), include=["documents","metadatas","distances"])
            return [{"chunk_id":i,"text":t,"document_id":m["document_id"],
                     "similarity":round(1-float(d), 6)}
                    for i,t,m,d in zip(result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0])]

    def calibrate(self, strategy):
        inside = [{"query":q,"similarity":self.retrieve(q,strategy,self.collections[strategy].count())[0]["similarity"]} for q in CALIBRATION_IN]
        outside = [{"query":q,"similarity":self.retrieve(q,strategy,self.collections[strategy].count())[0]["similarity"]} for q in CALIBRATION_OUT]
        lower, upper = max(x["similarity"] for x in outside), min(x["similarity"] for x in inside)
        if lower >= upper:
            raise ValueError("Calibration clusters overlap: inspect evidence before selecting a threshold")
        return {"in_scope":inside,"out_of_scope":outside,"threshold":round((lower+upper)/2,6),
                "method":"midpoint(max out-of-scope, min in-scope)"}

    def answer(self, query):
        with self.lock:
            key = (normalize(query).casefold(), self.strategy, self.revision)
            if key in self.cache:
                return {**self.cache[key], "cache_hit": True}
            chunks = self.retrieve(query)
            supported = chunks[0]["similarity"] >= self.calibration[self.strategy]["threshold"]
            # The best matching document supplies the answer; only retrieved chunk text is used.
            relevant = [c for c in chunks if c["document_id"] == chunks[0]["document_id"]] if supported else []
            self.generation_calls += 1
            answer = compose_context(relevant) if supported else FALLBACK
            result = {"answer":answer,"chunks":relevant,"retrieved":chunks,
                      "citations":sorted({c["document_id"] for c in relevant}),
                      "fallback":not supported,"cache_hit":False}
            if len(self.cache) >= 256:
                self.cache.pop(next(iter(self.cache)))
            self.cache[key] = result
            return result

    def add_document(self, doc):
        with self.lock:
            # Build candidate collections off to the side. This avoids stale ANN search
            # state after deletes and makes failed calibration an atomic rollback.
            import uuid
            candidate_documents = {**self.documents, doc.document_id:doc}
            previous_collections = self.collections
            namespace = uuid.uuid4().hex[:8]
            candidates = {strategy:self.client.create_collection(f"practo_{strategy}_{namespace}",
                metadata={"hnsw:space":"cosine"},embedding_function=None) for strategy in STRATEGIES}
            self.collections = candidates
            try:
                for strategy in STRATEGIES:
                    self._index(list(candidate_documents.values()),strategy)
                calibration = {strategy:self.calibrate(strategy) for strategy in STRATEGIES}
            except Exception:
                self.collections = previous_collections
                for collection in candidates.values():
                    self.client.delete_collection(collection.name)
                raise
            self.documents = candidate_documents
            self.revision += 1
            self.cache.clear()
            self.calibration = calibration
            for collection in previous_collections.values():
                self.client.delete_collection(collection.name)
            return self.revision



def compose_context(chunks):
    # Restore source chunk order; remove identical overlapping sentences.
    ordered = sorted(chunks, key=lambda c:int(c["chunk_id"].rsplit("-",1)[1]))
    seen = set()
    result = []
    for c in ordered:
        for sentence in sentences(c["text"]):
            if sentence not in seen:
                result.append(sentence)
                seen.add(sentence)
    return " ".join(result)

