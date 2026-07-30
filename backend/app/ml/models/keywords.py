"""TF-IDF + simplified YAKE keyword extraction."""

import re
import math
from typing import List, Dict
from collections import Counter

STOPWORDS = {
    'the','a','an','is','it','in','on','at','to','for','of','and','or','but','this','that',
    'with','from','by','as','be','was','were','are','have','has','had','do','did','will',
    'would','could','should','may','might','shall','can','not','no','nor','so','yet','both',
    'either','neither','each','few','more','most','other','some','such','than','too','very',
    'just','because','if','while','although','though','however','therefore','thus','hence',
    'i','we','you','he','she','they','its','our','your','their','my','his','her','about','also','been',
}


class KeywordExtractor:
    def extract(self, text: str, top_n: int = 20, ngram_range: tuple = (1, 3)) -> Dict:
        text = re.sub(r'\[PAGE \d+\]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        tfidf_kws = self._tfidf(text, top_n, ngram_range)
        yake_kws = self._yake(text, top_n)

        merged = {}
        for kw in tfidf_kws:
            merged[kw["keyword"]] = {**kw, "method": "tfidf"}
        for kw in yake_kws:
            if kw["keyword"] in merged:
                merged[kw["keyword"]]["score"] = round((merged[kw["keyword"]]["score"] + kw["score"]) / 2, 4)
            else:
                merged[kw["keyword"]] = {**kw, "method": "yake"}

        all_kws = sorted(merged.values(), key=lambda x: -x["score"])[:top_n]
        unigrams = [k for k in all_kws if len(k["keyword"].split()) == 1][:10]
        phrases = [k for k in all_kws if len(k["keyword"].split()) > 1][:10]

        return {"keywords": all_kws, "top_unigrams": unigrams, "top_phrases": phrases}

    def _tfidf(self, text: str, top_n: int, ngram_range: tuple) -> List[Dict]:
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50] or [text]
        min_n, max_n = ngram_range
        doc_tf = []

        for para in paragraphs:
            words = [w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', para) if w.lower() not in STOPWORDS]
            ngrams = []
            for n in range(min_n, max_n + 1):
                ngrams += [' '.join(words[i:i+n]) for i in range(len(words) - n + 1)]
            doc_tf.append(Counter(ngrams))

        N = len(doc_tf)
        df = Counter()
        for tf in doc_tf:
            df.update(set(tf.keys()))
        global_tf = Counter()
        for tf in doc_tf:
            global_tf.update(tf)

        scores = {}
        for term, count in global_tf.items():
            if count < 2:
                continue
            idf = math.log((N + 1) / (df[term] + 1)) + 1
            scores[term] = round(count * idf, 4)

        max_score = max(scores.values()) if scores else 1
        return [
            {"keyword": k, "score": round(v/max_score, 4), "count": global_tf[k]}
            for k, v in sorted(scores.items(), key=lambda x: -x[1])[:top_n]
        ]

    def _yake(self, text: str, top_n: int) -> List[Dict]:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        words_filtered = [w for w in words if w not in STOPWORDS]
        if not words_filtered:
            return []

        freq = Counter(words_filtered)
        total = len(words_filtered)
        first_pos = {}
        for i, w in enumerate(words_filtered):
            if w not in first_pos:
                first_pos[w] = i / max(total, 1)

        bigrams = [f"{words_filtered[i]} {words_filtered[i+1]}" for i in range(len(words_filtered) - 1)]
        bigram_freq = Counter(bigrams)

        candidates = {}
        for word, count in freq.most_common(50):
            tf_score = count / total
            pos_score = 1 - first_pos.get(word, 1)
            candidates[word] = round((tf_score + pos_score) / 2, 4)
        for phrase, count in bigram_freq.most_common(30):
            if count >= 2:
                candidates[phrase] = round((count / max(len(bigrams), 1)) * 1.2, 4)

        max_s = max(candidates.values()) if candidates else 1
        return [
            {"keyword": k, "score": round(v/max_s, 4), "count": freq.get(k, bigram_freq.get(k, 1))}
            for k, v in sorted(candidates.items(), key=lambda x: -x[1])[:top_n]
        ]


keyword_extractor = KeywordExtractor()
