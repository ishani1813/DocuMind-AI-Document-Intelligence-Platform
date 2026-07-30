"""Named Entity Recognition with regex fallback."""

import re
from typing import List, Dict
from collections import defaultdict
import structlog

logger = structlog.get_logger()
ENTITY_LABELS = {"PER": "Person", "ORG": "Organization", "LOC": "Location", "MISC": "Miscellaneous"}


class NERExtractor:
    def __init__(self):
        self._pipeline = None

    def _load(self):
        if self._pipeline is None:
            try:
                from transformers import pipeline
                self._pipeline = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple", device=-1)
            except Exception as e:
                logger.warning("NER model unavailable, using regex fallback", error=str(e))
                self._pipeline = None

    def extract(self, text: str, top_n: int = 20) -> Dict:
        self._load()
        snippet = text[:3000]
        entities = self._model_extract(snippet) if self._pipeline else self._regex_extract(snippet)

        agg = defaultdict(int)
        for ent in entities:
            agg[(ent["text"].strip(), ent["label"])] += 1

        sorted_ents = sorted(agg.items(), key=lambda x: -x[1])[:top_n]
        result_list = [{"text": k[0], "label": k[1], "count": v} for k, v in sorted_ents]

        by_type = defaultdict(list)
        for ent in result_list:
            by_type[ent["label"]].append(ent["text"])

        return {"entities": result_list, "by_type": dict(by_type), "total": len(result_list)}

    def _model_extract(self, text: str) -> List[Dict]:
        try:
            raw = self._pipeline(text)
            return [
                {"text": e["word"].replace("##", ""), "label": ENTITY_LABELS.get(e["entity_group"], e["entity_group"])}
                for e in raw if e.get("score", 0) > 0.85 and len(e["word"]) > 1
            ]
        except Exception as e:
            logger.error("NER extraction failed", error=str(e))
            return self._regex_extract(text)

    def _regex_extract(self, text: str) -> List[Dict]:
        entities = []
        date_pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        for m in re.finditer(date_pattern, text):
            entities.append({"text": m.group(), "label": "Date"})
        for m in re.finditer(r'\$[\d,]+(?:\.\d{2})?(?:\s?(?:million|billion|thousand))?', text):
            entities.append({"text": m.group(), "label": "Money"})
        for m in re.finditer(r'\b\d+(?:\.\d+)?%', text):
            entities.append({"text": m.group(), "label": "Percent"})
        for m in re.finditer(r'\b([A-Z][a-z]+ (?:[A-Z][a-z]+ ?){1,3})\b', text):
            word = m.group().strip()
            if len(word) > 4:
                entities.append({"text": word, "label": "Person"})
        return entities


ner_extractor = NERExtractor()
