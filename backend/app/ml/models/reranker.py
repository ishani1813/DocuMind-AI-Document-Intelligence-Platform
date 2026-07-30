"""Cross-encoder re-ranking for improved RAG retrieval precision."""

from typing import List, Dict
import structlog

logger = structlog.get_logger()


class CrossEncoderReranker:
    def __init__(self):
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
            except Exception as e:
                logger.warning("Cross-encoder unavailable", error=str(e))
                self._model = None

    def rerank(self, query: str, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
        if not chunks:
            return chunks
        self._load()
        if self._model is None:
            return chunks[:top_k]

        pairs = [(query, c["chunk_text"]) for c in chunks]
        try:
            scores = self._model.predict(pairs)
            for chunk, score in zip(chunks, scores):
                chunk["rerank_score"] = round(float(score), 4)
            return sorted(chunks, key=lambda x: -x.get("rerank_score", 0))[:top_k]
        except Exception as e:
            logger.error("Re-ranking failed", error=str(e))
            return chunks[:top_k]


cross_encoder_reranker = CrossEncoderReranker()
