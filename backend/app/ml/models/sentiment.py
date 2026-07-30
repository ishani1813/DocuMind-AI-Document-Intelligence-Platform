"""Document & chunk-level sentiment analysis with lexicon fallback."""

import re
from typing import List, Dict
import structlog

logger = structlog.get_logger()
POS_WORDS = {'excellent','great','good','positive','success','strong','improve','growth','benefit','profit','gain','innovative','effective','efficient','outstanding','best','increase'}
NEG_WORDS = {'poor','bad','negative','failure','weak','decline','loss','risk','problem','issue','concern','deficit','decrease','liability','delay','breach','penalty','lawsuit','downturn'}


class SentimentAnalyzer:
    def __init__(self):
        self._pipeline = None

    def _load(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
                self._pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english", device=-1, truncation=True, max_length=512)
            except Exception as e:
                logger.warning("Sentiment model unavailable, using lexicon fallback", error=str(e))
                self._pipeline = None

    def analyze(self, text: str) -> Dict:
        self._load()
        snippet = text[:512]
        return self._model_analyze(snippet) if self._pipeline else self._lexicon_analyze(snippet)

    def analyze_chunks(self, chunks: List[str]) -> Dict:
        self._load()
        results = []
        dist = {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0}

        for i, chunk in enumerate(chunks[:30]):
            result = self._model_analyze(chunk[:512]) if self._pipeline else self._lexicon_analyze(chunk)
            label = result["label"]
            dist[label] = dist.get(label, 0) + 1
            results.append({"index": i, "label": label, "score": result["score"], "snippet": chunk[:120]})

        total = len(results) or 1
        pos_score = sum(r["score"] for r in results if r["label"] == "POSITIVE")
        neg_score = sum(r["score"] for r in results if r["label"] == "NEGATIVE")
        overall = {"label": "POSITIVE", "score": round(pos_score/total, 3)} if pos_score >= neg_score else {"label": "NEGATIVE", "score": round(neg_score/total, 3)}

        return {"overall": overall, "chunks": results, "distribution": dist}

    def _model_analyze(self, text: str) -> Dict:
        try:
            r = self._pipeline(text)[0]
            label, score = r["label"], round(r["score"], 4)
            return {"label": label, "score": score, "breakdown": {
                "positive": score if label == "POSITIVE" else round(1-score, 4),
                "negative": score if label == "NEGATIVE" else round(1-score, 4),
            }}
        except Exception as e:
            logger.error("Sentiment analysis failed", error=str(e))
            return self._lexicon_analyze(text)

    def _lexicon_analyze(self, text: str) -> Dict:
        words = set(re.findall(r'\w+', text.lower()))
        pos, neg = len(words & POS_WORDS), len(words & NEG_WORDS)
        total = pos + neg or 1
        if pos > neg:
            score, label = round(0.5 + (pos/total)*0.5, 3), "POSITIVE"
        elif neg > pos:
            score, label = round(0.5 + (neg/total)*0.5, 3), "NEGATIVE"
        else:
            score, label = 0.5, "NEUTRAL"
        return {"label": label, "score": score, "breakdown": {"positive": pos/total, "negative": neg/total}}


sentiment_analyzer = SentimentAnalyzer()
