"""
Enhanced RAG Pipeline — HyDE query rewriting + cross-encoder re-ranking.
Fully instrumented through LLMOps for cost/latency/quality tracking.
"""

from typing import List, Optional, Dict
import structlog

from app.core.config import settings
from app.ml.models.reranker import cross_encoder_reranker
from app.llmops import llmops_tracker

logger = structlog.get_logger()


class HyDEPipeline:
    """Hypothetical Document Embeddings — rewrites vague queries into hypothetical answers for better retrieval."""

    async def rewrite_query(self, query: str, user_id: Optional[str] = None) -> str:
        prompt = f"""Write a short passage (3-5 sentences) that would directly answer this question.
Write as if you are the document that contains this information. Do not mention that you are generating a hypothetical.

Question: {query}

Passage:"""

        model_name = settings.OLLAMA_MODEL if settings.USE_OLLAMA else "gpt-3.5-turbo"
        provider = "ollama" if settings.USE_OLLAMA else "openai"

        async with llmops_tracker.track(operation="hyde_rewrite", model=model_name, provider=provider, user_id=user_id) as t:
            t.set_input(query)
            try:
                if settings.USE_OLLAMA:
                    hypothetical = await self._ollama_complete(prompt)
                else:
                    hypothetical = await self._openai_complete(prompt)
                t.set_output(hypothetical)
                logger.info("HyDE rewritten", original=query[:50], hypothetical=hypothetical[:50])
                return hypothetical
            except Exception as e:
                logger.warning("HyDE failed, using original query", error=str(e))
                t.set_output(query)
                return query

    async def _openai_complete(self, prompt: str) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=150,
        )
        return response.choices[0].message.content.strip()

    async def _ollama_complete(self, prompt: str) -> str:
        import ollama
        import asyncio
        loop = asyncio.get_event_loop()

        def _sync():
            client = ollama.Client(host=settings.OLLAMA_BASE_URL)
            response = client.chat(model=settings.OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])
            return response["message"]["content"].strip()

        return await loop.run_in_executor(None, _sync)


class RAGWithRerank:
    """Full enhanced RAG: HyDE query rewriting + retrieval + cross-encoder re-ranking + generation."""

    def __init__(self):
        self.hyde = HyDEPipeline()

    async def query(
        self, query: str, owner_id: str, conversation_history: List[Dict],
        document_ids: Optional[List[str]] = None, workspace_id: Optional[str] = None,
        use_hyde: bool = False, use_rerank: bool = True,
        top_k: int = 10, final_k: int = 5,
    ) -> dict:
        from app.services.rag_service import rag_service

        retrieval_query = query
        hyde_used = False
        if use_hyde:
            retrieval_query = await self.hyde.rewrite_query(query, user_id=owner_id)
            hyde_used = True

        retrieved = await rag_service.semantic_search(
            query=retrieval_query, owner_id=owner_id,
            document_ids=document_ids, workspace_id=workspace_id,
            top_k=top_k if use_rerank else final_k,
        )

        if not retrieved:
            return {"answer": "I couldn't find relevant information in the uploaded documents.", "sources": [], "reranked": False, "hyde_used": hyde_used}

        reranked = False
        if use_rerank and len(retrieved) > final_k:
            retrieved = cross_encoder_reranker.rerank(query=query, chunks=retrieved, top_k=final_k)
            reranked = True

        context_parts = [
            f"[Source {i+1}: {c['document_title']}, Page {c['page_number']}]\n{c['chunk_text']}"
            for i, c in enumerate(retrieved[:final_k])
        ]
        context = "\n\n---\n\n".join(context_parts)

        SYSTEM = f"""You are DocuMind. Answer ONLY from the provided context. Cite sources by document and page.

Context:
{context}"""

        messages = [{"role": "system", "content": SYSTEM}]
        for msg in conversation_history[-8:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": query})

        model_name = settings.OLLAMA_MODEL if settings.USE_OLLAMA else settings.OPENAI_MODEL
        provider = "ollama" if settings.USE_OLLAMA else "openai"

        async with llmops_tracker.track(operation="rag_chat_enhanced", model=model_name, provider=provider, user_id=owner_id) as t:
            t.set_input(query)
            avg_score = sum(c.get("rerank_score", c["relevance_score"]) for c in retrieved[:final_k]) / max(len(retrieved[:final_k]), 1)
            t.set_rag_metadata(chunk_count=len(retrieved[:final_k]), avg_score=avg_score, used_hyde=hyde_used, used_rerank=reranked)

            try:
                if settings.USE_OLLAMA:
                    answer = await self._ollama_chat(messages)
                else:
                    answer = await self._openai_chat(messages)
                t.set_output(answer)
            except Exception as e:
                answer = f"AI model error: {str(e)[:200]}"
                t.set_output(answer)

        sources = [
            {
                "document_id": c["document_id"], "document_title": c["document_title"],
                "page_number": c["page_number"],
                "chunk_text": c["chunk_text"][:300] + ("..." if len(c["chunk_text"]) > 300 else ""),
                "relevance_score": c.get("rerank_score", c.get("relevance_score", 0.0)),
            }
            for c in retrieved[:final_k]
        ]

        return {"answer": answer, "sources": sources, "reranked": reranked, "hyde_used": hyde_used}

    async def _openai_chat(self, messages: List[dict]) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(model=settings.OPENAI_MODEL, messages=messages, temperature=0.1, max_tokens=2000)
        return response.choices[0].message.content

    async def _ollama_chat(self, messages: List[dict]) -> str:
        import ollama
        import asyncio
        loop = asyncio.get_event_loop()

        def _sync():
            client = ollama.Client(host=settings.OLLAMA_BASE_URL)
            response = client.chat(model=settings.OLLAMA_MODEL, messages=messages)
            return response["message"]["content"]

        return await loop.run_in_executor(None, _sync)


class DocumentAnalysisPipeline:
    """Runs all ML models concurrently on document text."""

    async def analyze(self, document_id: str, text: str, chunks: Optional[List[str]] = None) -> Dict:
        import asyncio
        from app.ml.models import document_classifier, document_summarizer, ner_extractor, sentiment_analyzer, keyword_extractor

        loop = asyncio.get_event_loop()
        results = await asyncio.gather(
            loop.run_in_executor(None, document_classifier.classify, text),
            loop.run_in_executor(None, document_summarizer.summarize, text, "extractive", 5, 150),
            loop.run_in_executor(None, ner_extractor.extract, text, 15),
            loop.run_in_executor(None, sentiment_analyzer.analyze, text),
            loop.run_in_executor(None, keyword_extractor.extract, text, 15),
        )
        classification, summary, entities, sentiment, keywords = results

        chunk_sentiment = None
        if chunks:
            chunk_sentiment = await loop.run_in_executor(None, sentiment_analyzer.analyze_chunks, chunks)

        return {
            "document_id": document_id, "classification": classification, "summary": summary,
            "entities": entities, "sentiment": sentiment, "chunk_sentiment": chunk_sentiment, "keywords": keywords,
        }


hyde_pipeline = HyDEPipeline()
rag_with_rerank = RAGWithRerank()
document_analysis_pipeline = DocumentAnalysisPipeline()
