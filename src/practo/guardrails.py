"""Deterministic guardrails; scope and limitations are documented in GOVERNANCE.md."""
import re
import unicodedata

FALLBACK = "I don't know based on the available clinic policy documents. Please contact clinic support."
PHONE = re.compile(r"(?<!\w)(?:\+?91[\s-]?)?[6-9](?:[\s-]?\d){9}(?!\w)")
INJECTION = re.compile(
    r"ignore\s+(?:all\s+|the\s+|any\s+)?(?:previous|prior|system|above)\s+(?:instructions?|rules?)"
    r"|(?:reveal|print|show|override)\s+(?:the\s+|your\s+)?(?:system\s+prompt|secrets?|api\s*keys?)"
    r"|you\s+are\s+now\s+(?:an?\s+)?(?:admin|unrestricted)"
    r"|\[/?INST\]|<\|(?:system|im_start)\|>", re.I)


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).split())


def mask_pii(text):
    return PHONE.sub("[PHONE_MASKED]", unicodedata.normalize("NFKC", text))


def injection_detected(text):
    return bool(INJECTION.search(normalize(text)))


def grounded(answer, allowed_answer):
    """Extractive MOCK_LLM allows only the evidence-derived canonical answer.

    Strict equality intentionally rejects even an unsupported appended sentence.
    This is conservative text validation, not general semantic entailment.
    """
    return normalize(answer) == normalize(allowed_answer)

