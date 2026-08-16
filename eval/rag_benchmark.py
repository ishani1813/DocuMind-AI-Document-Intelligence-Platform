#!/usr/bin/env python3
"""
DocuMind RAG Evaluation Benchmark
==================================

Compares two arms of DocuMind's own live API, both served by the same
endpoint (`/api/v1/ml/chat/enhanced`) with different flags:

  baseline  = plain vector search only        (use_hyde=False, use_rerank=False)
  enhanced  = HyDE query expansion + rerank    (use_hyde=True,  use_rerank=True)

For each test question it records, per arm:
  - Recall@5, Precision@5, MRR      (needs relevant_documents in the test set)
  - Faithfulness, Answer Relevance  (LLM-as-judge; skip with --skip-judge)
  - Latency (mean, P50, P95)        (always measured, wall-clock)

Nothing here is invented — every number comes from an actual call to your
running DocuMind instance. If the instance isn't reachable or a call fails,
that row is recorded as an error and excluded from the averages (not
silently zeroed).

Usage:
    python rag_benchmark.py --testset testset.example.json \\
        --base-url http://localhost:8000 \\
        --email you@example.com --password yourpassword

See README.md in this folder for how to build a test set and get a token.
"""

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass
from typing import Optional

import requests


# ── Config ───────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "http://localhost:8000"
ENHANCED_ENDPOINT = "/api/v1/ml/chat/enhanced"
SESSIONS_ENDPOINT = "/api/v1/chat/sessions"
LOGIN_ENDPOINT = "/api/v1/auth/login"

# Both arms hit the same endpoint DocuMind already ships — see
# backend/app/api/v1/ml.py (EnhancedChatRequest) and
# backend/app/ml/pipelines/__init__.py (RAGWithRerank.query). final_k is
# fixed at 5 server-side, so both arms return up to 5 sources -> @5 metrics
# line up directly.
ARMS = {
    "baseline": {"use_hyde": False, "use_rerank": False, "top_k": 5},
    "enhanced": {"use_hyde": True, "use_rerank": True, "top_k": 10},
}


# ── Data classes ─────────────────────────────────────────────────────────

@dataclass
class TestCase:
    id: str
    question: str
    relevant: list          # [{"document_id": str, "page_number": int|None}, ...]
    document_ids: Optional[list] = None   # restrict retrieval scope, optional


# ── API client ───────────────────────────────────────────────────────────

class DocuMindClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def create_chat_session(self) -> str:
        r = self.session.post(f"{self.base_url}{SESSIONS_ENDPOINT}", json={})
        r.raise_for_status()
        return r.json()["id"]

    def enhanced_chat(self, session_id, query, document_ids=None,
                       use_hyde=False, use_rerank=True, top_k=10, timeout=90):
        payload = {
            "query": query,
            "session_id": session_id,
            "document_ids": document_ids,
            "use_hyde": use_hyde,
            "use_rerank": use_rerank,
            "top_k": top_k,
        }
        start = time.perf_counter()
        r = self.session.post(f"{self.base_url}{ENHANCED_ENDPOINT}", json=payload, timeout=timeout)
        latency_ms = (time.perf_counter() - start) * 1000
        r.raise_for_status()
        return r.json(), latency_ms


def login(base_url: str, email: str, password: str) -> str:
    r = requests.post(f"{base_url.rstrip('/')}{LOGIN_ENDPOINT}", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


# ── Retrieval metrics ────────────────────────────────────────────────────

def _is_relevant(source: dict, rel: dict) -> bool:
    if source.get("document_id") != rel.get("document_id"):
        return False
    if rel.get("page_number") is None:
        return True
    return source.get("page_number") == rel.get("page_number")


def recall_at_k(sources, relevant, k=5):
    if not relevant:
        return None
    top = sources[:k]
    hits = sum(1 for rel in relevant if any(_is_relevant(s, rel) for s in top))
    return hits / len(relevant)


def precision_at_k(sources, relevant, k=5):
    if not relevant:
        return None
    top = sources[:k]
    if not top:
        return 0.0
    hits = sum(1 for s in top if any(_is_relevant(s, rel) for rel in relevant))
    return hits / len(top)


def reciprocal_rank(sources, relevant):
    if not relevant:
        return None
    for i, s in enumerate(sources, start=1):
        if any(_is_relevant(s, rel) for rel in relevant):
            return 1.0 / i
    return 0.0


# ── LLM-as-judge (faithfulness + answer relevance) ─────────────────────────

JUDGE_PROMPT = """You are evaluating a RAG system's answer for two things.

Question: {question}

Retrieved context the system was given:
{context}

System's answer:
{answer}

Score two things from 0.0 to 1.0 and return ONLY JSON, no other text:
1. "faithfulness": what fraction of the answer's claims are directly supported
   by the retrieved context above? 1.0 = fully grounded, 0.0 = entirely
   unsupported or fabricated. If the answer correctly says it couldn't find
   the information, faithfulness = 1.0.
2. "answer_relevance": does the answer actually address the question asked?
   1.0 = fully addresses it, 0.0 = off-topic or a non-answer.

Return exactly: {{"faithfulness": <float>, "answer_relevance": <float>}}"""


class Judge:
    """LLM-as-judge. Deliberately independent of the app's own OpenAI/Ollama
    choice -- you can (and should) judge with a different, ideally stronger,
    model than the one being evaluated to reduce self-preference bias."""

    def __init__(self, provider="openai", model=None, openai_api_key=None, ollama_base_url=None):
        self.provider = provider
        if provider == "openai":
            from openai import OpenAI
            key = openai_api_key or os.environ.get("OPENAI_API_KEY")
            if not key:
                raise RuntimeError("Set OPENAI_API_KEY (or pass --judge-provider ollama)")
            self.client = OpenAI(api_key=key)
            self.model = model or "gpt-4o-mini"
        elif provider == "ollama":
            import ollama
            self.client = ollama.Client(host=ollama_base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
            self.model = model or "llama3"
        else:
            raise ValueError(f"Unknown judge provider: {provider}")

    def score(self, question: str, context: str, answer: str) -> dict:
        prompt = JUDGE_PROMPT.format(question=question, context=context[:6000], answer=answer)
        try:
            if self.provider == "openai":
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=100,
                )
                text = resp.choices[0].message.content
            else:
                resp = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
                text = resp["message"]["content"]
            text = text.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.lower().startswith("json"):
                    text = text[4:]
                text = text.strip()
            data = json.loads(text)
            return {
                "faithfulness": float(data.get("faithfulness")),
                "answer_relevance": float(data.get("answer_relevance")),
            }
        except Exception as e:
            return {"faithfulness": None, "answer_relevance": None, "judge_error": str(e)}


# ── Benchmark runner ─────────────────────────────────────────────────────

def run_arm(client: DocuMindClient, case: TestCase, arm_name: str, judge: Optional[Judge]) -> dict:
    cfg = ARMS[arm_name]
    try:
        session_id = client.create_chat_session()
        result, latency_ms = client.enhanced_chat(
            session_id=session_id,
            query=case.question,
            document_ids=case.document_ids,
            use_hyde=cfg["use_hyde"],
            use_rerank=cfg["use_rerank"],
            top_k=cfg["top_k"],
        )
    except Exception as e:
        return {"case_id": case.id, "arm": arm_name, "error": str(e)}

    sources = result.get("sources", []) or []
    answer = result.get("answer", "")

    row = {
        "case_id": case.id,
        "arm": arm_name,
        "latency_ms": latency_ms,
        "recall_at_5": recall_at_k(sources, case.relevant, k=5),
        "precision_at_5": precision_at_k(sources, case.relevant, k=5),
        "rr": reciprocal_rank(sources, case.relevant),
        "answer": answer,
        "sources": sources,
    }

    if judge is not None:
        context = "\n\n".join(
            f"[{s.get('document_title')} p.{s.get('page_number')}] {s.get('chunk_text', '')}"
            for s in sources
        )
        row.update(judge.score(case.question, context, answer))

    return row


def load_testset(path: str) -> list:
    with open(path) as f:
        raw = json.load(f)
    return [
        TestCase(
            id=item["id"],
            question=item["question"],
            relevant=item.get("relevant_documents", []),
            document_ids=item.get("document_ids"),
        )
        for item in raw
    ]


def summarize(rows: list, arm_name: str) -> dict:
    arm_rows = [r for r in rows if r["arm"] == arm_name and not r.get("error")]
    if not arm_rows:
        return {}

    def avg(key):
        vals = [r[key] for r in arm_rows if r.get(key) is not None]
        return round(statistics.mean(vals), 4) if vals else None

    def pct(key, p):
        vals = sorted(r[key] for r in arm_rows if r.get(key) is not None)
        if not vals:
            return None
        idx = min(int(len(vals) * p), len(vals) - 1)
        return round(vals[idx], 1)

    return {
        "n": len(arm_rows),
        "recall_at_5": avg("recall_at_5"),
        "precision_at_5": avg("precision_at_5"),
        "mrr": avg("rr"),
        "faithfulness": avg("faithfulness"),
        "answer_relevance": avg("answer_relevance"),
        "latency_ms_mean": avg("latency_ms"),
        "latency_ms_p50": pct("latency_ms", 0.50),
        "latency_ms_p95": pct("latency_ms", 0.95),
    }


def print_report(summary_baseline: dict, summary_enhanced: dict):
    def fmt(v):
        return "\u2014" if v is None else str(v)

    rows = [
        ("N (questions)", summary_baseline.get("n"), summary_enhanced.get("n")),
        ("Recall@5", summary_baseline.get("recall_at_5"), summary_enhanced.get("recall_at_5")),
        ("Precision@5", summary_baseline.get("precision_at_5"), summary_enhanced.get("precision_at_5")),
        ("MRR", summary_baseline.get("mrr"), summary_enhanced.get("mrr")),
        ("Faithfulness", summary_baseline.get("faithfulness"), summary_enhanced.get("faithfulness")),
        ("Answer relevance", summary_baseline.get("answer_relevance"), summary_enhanced.get("answer_relevance")),
        ("Latency mean (ms)", summary_baseline.get("latency_ms_mean"), summary_enhanced.get("latency_ms_mean")),
        ("Latency P50 (ms)", summary_baseline.get("latency_ms_p50"), summary_enhanced.get("latency_ms_p50")),
        ("Latency P95 (ms)", summary_baseline.get("latency_ms_p95"), summary_enhanced.get("latency_ms_p95")),
    ]

    label_w = max(len(r[0]) for r in rows) + 2
    print(f"\n{'Metric':<{label_w}}{'Baseline':>12}{'Enhanced':>12}")
    print("-" * (label_w + 24))
    for label, b, e in rows:
        print(f"{label:<{label_w}}{fmt(b):>12}{fmt(e):>12}")
    print()

    r_b, r_e = summary_baseline.get("recall_at_5"), summary_enhanced.get("recall_at_5")
    l_b, l_e = summary_baseline.get("latency_ms_mean"), summary_enhanced.get("latency_ms_mean")
    if r_b is not None and r_e is not None and l_b is not None and l_e is not None:
        recall_delta_pts = (r_e - r_b) * 100
        latency_delta = l_e - l_b
        r_word = "improved" if recall_delta_pts >= 0 else "reduced"
        l_word = "increasing" if latency_delta >= 0 else "decreasing"
        print(
            f'"Enhanced retrieval {r_word} Recall@5 by {abs(recall_delta_pts):.1f} points '
            f'while {l_word} mean latency by {abs(latency_delta):.0f} ms."'
        )
    print(
        "\nNote: with a small test set these numbers are directional, not "
        "statistically robust -- treat them as a starting point, and grow the "
        "test set before quoting a precise percentage."
    )


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DocuMind RAG evaluation benchmark")
    parser.add_argument("--testset", required=True, help="Path to test set JSON")
    parser.add_argument("--base-url", default=os.environ.get("DOCUMIND_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--email", default=os.environ.get("DOCUMIND_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("DOCUMIND_PASSWORD"))
    parser.add_argument("--token", default=os.environ.get("DOCUMIND_TOKEN"), help="Skip login, use an existing JWT")
    parser.add_argument("--skip-judge", action="store_true", help="Skip faithfulness/answer-relevance (retrieval + latency only)")
    parser.add_argument("--judge-provider", default=os.environ.get("JUDGE_PROVIDER", "openai"), choices=["openai", "ollama"])
    parser.add_argument("--judge-model", default=os.environ.get("JUDGE_MODEL"))
    parser.add_argument("--out", default="benchmark_results.json", help="Where to write raw per-question results")
    args = parser.parse_args()

    if not args.token:
        if not (args.email and args.password):
            sys.exit(
                "Provide --token, or --email/--password "
                "(or DOCUMIND_TOKEN / DOCUMIND_EMAIL+DOCUMIND_PASSWORD env vars) to authenticate."
            )
        try:
            token = login(args.base_url, args.email, args.password)
        except requests.RequestException as e:
            sys.exit(f"Login failed: {e}")
    else:
        token = args.token

    client = DocuMindClient(args.base_url, token)

    try:
        cases = load_testset(args.testset)
    except (OSError, json.JSONDecodeError, KeyError) as e:
        sys.exit(f"Could not load test set '{args.testset}': {e}")
    print(f"Loaded {len(cases)} test cases from {args.testset}")

    judge = None
    if not args.skip_judge:
        try:
            judge = Judge(provider=args.judge_provider, model=args.judge_model)
        except Exception as e:
            print(f"Warning: could not initialize judge ({e}). Continuing with retrieval + latency metrics only.")

    rows = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case.id}: {case.question[:60]}")
        for arm_name in ARMS:
            row = run_arm(client, case, arm_name, judge)
            if row.get("error"):
                print(f"  ! {arm_name} failed: {row['error']}")
            rows.append(row)

    with open(args.out, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nRaw results written to {args.out}")

    print_report(summarize(rows, "baseline"), summarize(rows, "enhanced"))


if __name__ == "__main__":
    main()
