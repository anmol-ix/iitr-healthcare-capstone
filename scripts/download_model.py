"""Setup ONLY: download the free model before running the network-disabled application."""
import os
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"
os.environ["HF_HUB_DISABLE_XET"] = "1"
from huggingface_hub import snapshot_download

if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[1] / "models/all-MiniLM-L6-v2"
    snapshot_download("sentence-transformers/all-MiniLM-L6-v2",
        revision="c9745ed1d9f207416be6d2e6f8de32d1f16199bf", local_dir=destination,
        allow_patterns=["*.json","*.txt","*.safetensors","1_Pooling/*"])
    print(f"Model ready at {destination}. All application runs use local_files_only=True.")

