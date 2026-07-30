"""Extractive + abstractive summarization."""

import re
from typing import Literal
from heapq import nlargest
import structlog

logger = structlog.get_logger()


class DocumentSummarizer:
    def __init__(self):
        self._pipeline = None

    def _load(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
                self._pipeline = pipeline("summarization", model="facebook/bart-large-cnn", device=-1)
            except Exception as e:
                logger.warning("Summarizer unavailable, using extractive fallback", error=str(e))
                self._pipeline = None

    def summarize(self, text: str, mode: Literal["extractive", "abstractive"] = "extractive",
                  max_sentences: int = 5, max_tokens: int = 150) -> dict:
        text = text.strip()
        if not text:
            return {"summary": "", "mode": mode, "word_count": 0}

        summary = self._abstractive(text, max_tokens) if mode == "abstractive" else self._extractive(text, max_sentences)
        return {"summary": summary, "mode": mode, "word_count": len(summary.split())}

    def _extractive(self, text: str, max_sentences: int = 5) -> str:
        text = re.sub(r'\[PAGE \d+\]', '', text)
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s.strip() for s in sentences if len(s.split()) > 5]

        if not sentences:
            return text[:500]
        if len(sentences) <= max_sentences:
            return " ".join(sentences)

        words = re.findall(r'\w+', text.lower())
        stopwords = {'the','a','an','is','it','in','on','at','to','for','of','and','or','but','this','that','with','from'}
        freq = {}
        for w in words:
            if w not in stopwords and len(w) > 2:
                freq[w] = freq.get(w, 0) + 1
        max_freq = max(freq.values()) if freq else 1
        freq = {w: v / max_freq for w, v in freq.items()}

        scores = {}
        for i, sent in enumerate(sentences):
            score = sum(freq.get(w.lower(), 0) for w in sent.split())
            if i == 0: score *= 1.5
            if i == len(sentences) - 1: score *= 1.2
            scores[sent] = score

        top = nlargest(max_sentences, scores, key=scores.get)
        return " ".join([s for s in sentences if s in top])

    def _abstractive(self, text: str, max_tokens: int = 150) -> str:
        self._load()
        if self._pipeline is None:
            return self._extractive(text, 4)
        snippet = text[:4000]
        try:
            result = self._pipeline(snippet, max_length=max_tokens, min_length=min(50, max_tokens // 2), do_sample=False)
            return result[0]["summary_text"]
        except Exception as e:
            logger.error("Abstractive summarization failed", error=str(e))
            return self._extractive(text, 4)


document_summarizer = DocumentSummarizer()
