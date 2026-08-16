# DocuMind RAG Evaluation Benchmark

Compares your **baseline** RAG path (plain vector search) against your
**enhanced** path (HyDE query expansion + cross-encoder reranking) — both
served by the `/api/v1/ml/chat/enhanced` endpoint that already exists in
your backend, just called with different flags. No new backend code is
needed to run this.

## 1. Prerequisites

- DocuMind running (`docker-compose up --build`), reachable at e.g.
  `http://localhost:8000`
- A user account (register one if you don't have one — see below)
- A judge model to score faithfulness/answer relevance: an `OPENAI_API_KEY`
  env var (uses `gpt-4o-mini` by default), or a local Ollama model with
  `--judge-provider ollama`. Skip this entirely with `--skip-judge` if you
  only want retrieval + latency numbers.

```bash
pip install -r requirements.txt
```

## 2. Get a test document set + document IDs

Upload 3-5 real PDFs through the app (or `POST /api/v1/documents/upload`),
wait for status `READY`, then:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/documents/
```

Note the `id` for each document you want to test against.

## 3. Write your test set

Copy `testset.example.json` and fill in real questions and real
`document_id` / `page_number` values — the page(s) that actually contain
the answer. This is the one part that has to be done by hand: nobody can
invent your ground truth for you. Aim for at least 15-20 questions,
covering a mix of easy lookups and harder multi-fact questions, so the
averages mean something.

`page_number: null` means "any page of this document counts as a hit" —
use that when you only care about document-level recall.

## 4. Get a token

Either let the script log in for you (`--email` / `--password`), or fetch
one yourself:

```bash
# Register once, if needed
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","full_name":"Your Name","password":"a-real-password-8plus-chars"}'

# Log in
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"a-real-password-8plus-chars"}'
```

## 5. Run it

```bash
python rag_benchmark.py \
  --testset testset.json \
  --base-url http://localhost:8000 \
  --email you@example.com --password yourpassword
```

Or with an existing token and no judge calls:

```bash
python rag_benchmark.py --testset testset.json --token "$TOKEN" --skip-judge
```

This prints a live progress line per question/arm, writes every raw
result (sources, answers, per-question scores) to `benchmark_results.json`,
and ends with a summary table plus an auto-generated one-line takeaway —
built from whatever numbers actually came back, nothing pre-written.

## What each metric means here

| Metric | How it's computed |
|---|---|
| Recall@5 | Of the relevant (document, page) pairs you labeled, what fraction appear anywhere in the top 5 returned sources |
| Precision@5 | Of the top 5 returned sources, what fraction are labeled relevant |
| MRR | 1 / rank of the first relevant source (0 if none in top 5) |
| Faithfulness | LLM-judge estimate of what fraction of the answer's claims are backed by the retrieved context |
| Answer relevance | LLM-judge estimate of whether the answer actually addresses the question |
| Latency | Wall-clock time for the full request (session create + retrieval + generation) |

## Honest caveats to keep in mind

- **Small test sets are noisy.** With 15-20 questions, a 0.1 difference in
  Recall@5 can flip with a handful of relabeled questions. Report the
  numbers, but don't oversell precision you don't have.
- **The judge model matters.** Faithfulness/relevance scores depend on
  which model is judging. Prefer a judge that's at least as strong as the
  model being evaluated, and say in your writeup which model judged.
- **This costs real API usage** — each question makes 2 generation calls
  (baseline + enhanced), the enhanced arm adds 1 HyDE rewrite call, and
  (unless `--skip-judge`) up to 2 more judge calls. Budget accordingly for
  larger test sets.
