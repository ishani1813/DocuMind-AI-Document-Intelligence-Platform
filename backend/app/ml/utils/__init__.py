"""Text preprocessing utilities and document clustering."""

import re
import math
from typing import List, Dict, Optional
import structlog

logger = structlog.get_logger()


class TextPreprocessor:
    def clean(self, text: str) -> str:
        text = re.sub(r'\[PAGE \d+\]', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()

    def sentence_split(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.split()) >= 3]

    def compute_stats(self, text: str) -> Dict:
        sentences = self.sentence_split(text)
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        avg_sent_len = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        return {
            "char_count": len(text), "word_count": len(words),
            "sentence_count": len(sentences), "paragraph_count": len(paragraphs),
            "avg_sentence_len": round(avg_sent_len, 1),
            "reading_time_min": round(len(words) / 200, 1),
        }

    def reading_level(self, text: str) -> Dict:
        sentences = self.sentence_split(text)
        words_raw = re.findall(r'\b[a-zA-Z]+\b', text)
        if not sentences or not words_raw:
            return {"score": 0, "level": "Unknown"}

        def syllable_count(word):
            word = word.lower()
            count = len(re.findall(r'[aeiou]+', word))
            if word.endswith('e') and count > 1:
                count -= 1
            return max(1, count)

        total_syllables = sum(syllable_count(w) for w in words_raw)
        asl = len(words_raw) / len(sentences)
        asw = total_syllables / len(words_raw)
        score = max(0, min(100, round(206.835 - 1.015 * asl - 84.6 * asw, 1)))

        if score >= 90: level = "Very Easy"
        elif score >= 70: level = "Easy"
        elif score >= 60: level = "Standard"
        elif score >= 50: level = "Fairly Difficult"
        elif score >= 30: level = "Difficult"
        else: level = "Very Difficult"

        return {"score": score, "level": level}


class DocumentClusterer:
    def cluster(self, documents: List[Dict], n_clusters: Optional[int] = None) -> Dict:
        if len(documents) < 2:
            return {
                "clusters": [{"id": 0, "label": "All Documents", "document_ids": [d["id"] for d in documents], "keywords": []}],
                "assignments": {d["id"]: 0 for d in documents},
            }
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.cluster import KMeans

            texts = [d.get("text", d.get("title", ""))[:2000] for d in documents]
            doc_ids = [d["id"] for d in documents]

            vectorizer = TfidfVectorizer(max_features=500, stop_words="english", ngram_range=(1, 2))
            X = vectorizer.fit_transform(texts)

            n_clusters = min(n_clusters or min(8, max(2, int(math.sqrt(len(documents))))), len(documents))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)

            feature_names = vectorizer.get_feature_names_out()
            clusters = []
            for i in range(n_clusters):
                center = kmeans.cluster_centers_[i]
                top_indices = center.argsort()[-5:][::-1]
                keywords = [feature_names[j] for j in top_indices]
                member_ids = [doc_ids[j] for j, l in enumerate(labels) if l == i]
                clusters.append({"id": i, "label": f"Topic: {', '.join(keywords[:2]).title()}", "document_ids": member_ids, "keywords": keywords, "size": len(member_ids)})

            assignments = {doc_ids[i]: int(labels[i]) for i in range(len(doc_ids))}
            return {"clusters": clusters, "assignments": assignments}
        except Exception as e:
            logger.error("Clustering failed", error=str(e))
            return {"clusters": [], "assignments": {}}


text_preprocessor = TextPreprocessor()
document_clusterer = DocumentClusterer()
