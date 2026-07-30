"""Zero-shot document classification using BART-large-MNLI, with keyword fallback."""

from typing import List, Dict, Optional
import structlog

logger = structlog.get_logger()

CANDIDATE_LABELS = [
    "legal document", "financial report", "medical document",
    "research paper", "technical documentation", "human resources",
    "marketing material", "general document",
]
LABEL_MAP = {
    "legal document": "Legal", "financial report": "Financial",
    "medical document": "Medical", "research paper": "Research",
    "technical documentation": "Technical", "human resources": "HR",
    "marketing material": "Marketing", "general document": "General",
}


class DocumentClassifier:
    def __init__(self):
        self._pipeline = None

    def _load(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
                logger.info("Loading zero-shot classifier...")
                self._pipeline = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
            except Exception as e:
                logger.warning("Classifier model unavailable, using fallback", error=str(e))
                self._pipeline = None

    def classify(self, text: str, custom_labels: Optional[List[str]] = None, top_k: int = 3) -> Dict:
        self._load()
        snippet = text[:2000]
        labels = custom_labels or CANDIDATE_LABELS

        if self._pipeline is None:
            return self._fallback(snippet, labels)

        try:
            result = self._pipeline(snippet, candidate_labels=labels, multi_label=False)
            mapped = [
                {"label": LABEL_MAP.get(l, l.title()), "score": round(s, 4)}
                for l, s in zip(result["labels"], result["scores"])
            ]
            return {"top_label": mapped[0]["label"], "top_score": mapped[0]["score"], "all_labels": mapped[:top_k]}
        except Exception as e:
            logger.error("Classification failed", error=str(e))
            return self._fallback(snippet, labels)

    def _fallback(self, text: str, labels: List[str]) -> Dict:
        text_lower = text.lower()
        keyword_map = {
            "Legal": ["contract", "agreement", "clause", "liability"],
            "Financial": ["revenue", "profit", "balance sheet", "fiscal"],
            "Medical": ["patient", "diagnosis", "treatment", "clinical"],
            "Research": ["abstract", "methodology", "hypothesis", "findings"],
            "Technical": ["api", "function", "algorithm", "architecture"],
            "HR": ["employee", "salary", "policy", "onboarding"],
            "Marketing": ["campaign", "brand", "conversion", "engagement"],
        }
        scores = {label: sum(1 for kw in kws if kw in text_lower) for label, kws in keyword_map.items()}
        top = max(scores, key=scores.get) if any(scores.values()) else "General"
        return {
            "top_label": top, "top_score": 0.6,
            "all_labels": [{"label": top, "score": 0.6}, {"label": "General", "score": 0.4}],
        }


document_classifier = DocumentClassifier()
