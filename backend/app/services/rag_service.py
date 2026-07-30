"""
RAG Service — Core retrieval-augmented generation engine.

Supports two LLM backends, switchable via USE_OLLAMA env var:
  - OpenAI (GPT-4 + ada-002 embeddings) — requires API key + credits
  - Ollama (Mistral/Llama3, local) — completely free, runs on your machine

Every call is tracked through the LLMOps tracker for cost/latency/quality observability.
"""

from typing import List, Optional, Dict
import structlog

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

from app.core.config import settings
from app.core.vector_store import get_chroma_client
from app.llmops import llmops_tracker, count_tokens_approx

logger = structlog.get_logger()

SYSTEM_PROMPT_TEMPLATE = """You are DocuMind, an intelligent document assistant. Answer questions based strictly on the provided document context.

Rules:
1. Answer ONLY from the provided context. Do not use outside knowledge.
2. If the context does not contain the answer, say: "I couldn't find that information in the uploaded documents."
3. Always cite sources by referencing the document name and page number.
4. Format clearly using bullet points or numbered lists when appropriate.
5. If multiple documents are relevant, synthesize information across them.

Context from documents:
{context}"""


def _get_embeddings():
    """Return the embedding function based on configured provider."""
    if settings.USE_OLLAMA:
        from langchain_community.embeddings import OllamaEmbeddings
        return OllamaEmbeddings(
            model=settings.OLLAMA_EMBED_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )
    else:
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )


class RAGService:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
        )
        self._embeddings = None

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = _get_embeddings()
        return self._embeddings

    def _get_vectorstore(self) -> Chroma:
        client = get_chroma_client()
        return Chroma(
            client=client,
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=self.embeddings,
        )

    # ── Ingestion ─────────────────────────────────────────────

    async def ingest_document(
        self,
        document_id: str,
        text_content: str,
        document_title: str,
        owner_id: str,
        workspace_id: Optional[str] = None,
        page_map: Optional[dict] = None,
    ) -> int:
        logger.info("Ingesting document", document_id=document_id, title=document_title)

        chunks = self.text_splitter.split_text(text_content)
        logger.info("Split document", chunks=len(chunks))

        metadatas, ids = [], []
        for i, chunk in enumerate(chunks):
            page_num = (page_map or {}).get(i, 1)
            metadatas.append({
                "document_id": document_id,
                "document_title": document_title,
                "owner_id": owner_id,
                "workspace_id": workspace_id or "",
                "page_number": page_num,
                "chunk_index": i,
            })
            ids.append(f"{document_id}_{i}")

        embed_model = settings.OLLAMA_EMBED_MODEL if settings.USE_OLLAMA else settings.OPENAI_EMBEDDING_MODEL
        async with llmops_tracker.track(
            operation="embedding_ingest",
            model=embed_model,
            provider="ollama" if settings.USE_OLLAMA else "openai",
            user_id=owner_id,
        ) as t:
            t.set_input(f"{len(chunks)} chunks from {document_title}")
            vectorstore = self._get_vectorstore()
            vectorstore.add_texts(texts=chunks, metadatas=metadatas, ids=ids)
            t.set_output(f"Embedded {len(chunks)} chunks", input_tokens=sum(count_tokens_approx(c) for c in chunks))

        logger.info("Document ingested", document_id=document_id, chunks=len(chunks))
        return len(chunks)

    async def delete_document_vectors(self, document_id: str):
        try:
            client = get_chroma_client()
            collection = client.get_collection(settings.CHROMA_COLLECTION_NAME)
            collection.delete(where={"document_id": document_id})
        except Exception as e:
            logger.warning("Could not delete vectors", document_id=document_id, error=str(e))

    # ── Retrieval ─────────────────────────────────────────────

    async def semantic_search(
        self,
        query: str,
        owner_id: str,
        document_ids: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[dict]:
        try:
            vectorstore = self._get_vectorstore()

            where_filter = {"owner_id": owner_id}
            if document_ids:
                where_filter = {"$and": [{"owner_id": owner_id}, {"document_id": {"$in": document_ids}}]}
            elif workspace_id:
                where_filter = {"$and": [{"owner_id": owner_id}, {"workspace_id": workspace_id}]}

            try:
                results = vectorstore.similarity_search_with_score(query=query, k=top_k, filter=where_filter)
            except Exception:
                results = vectorstore.similarity_search_with_score(query=query, k=top_k)

            output = []
            for doc, score in results:
                output.append({
                    "chunk_text": doc.page_content,
                    "document_id": doc.metadata.get("document_id", ""),
                    "document_title": doc.metadata.get("document_title", "Unknown"),
                    "page_number": doc.metadata.get("page_number", 1),
                    "relevance_score": round(max(0, 1 - float(score)), 4),
                })
            return output
        except Exception as e:
            logger.error("Semantic search failed", error=str(e))
            return []

    # ── RAG Chat ──────────────────────────────────────────────

    async def chat_with_documents(
        self,
        query: str,
        owner_id: str,
        conversation_history: List[dict],
        document_ids: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        retrieved = await self.semantic_search(
            query=query, owner_id=owner_id,
            document_ids=document_ids, workspace_id=workspace_id,
            top_k=settings.TOP_K_RESULTS,
        )

        if not retrieved:
            return {
                "answer": "I couldn't find any relevant information in the uploaded documents. Please upload documents first or try a different question.",
                "sources": [],
            }

        context_parts = [
            f"[Source {i+1}: {c['document_title']}, Page {c['page_number']}]\n{c['chunk_text']}"
            for i, c in enumerate(retrieved)
        ]
        context = "\n\n---\n\n".join(context_parts)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": query})

        model_name = settings.OLLAMA_MODEL if settings.USE_OLLAMA else settings.OPENAI_MODEL
        provider = "ollama" if settings.USE_OLLAMA else "openai"

        async with llmops_tracker.track(
            operation="rag_chat", model=model_name, provider=provider,
            user_id=owner_id, session_id=session_id,
        ) as t:
            t.set_input(query)
            avg_score = sum(c["relevance_score"] for c in retrieved) / len(retrieved)
            t.set_rag_metadata(chunk_count=len(retrieved), avg_score=avg_score)

            try:
                if settings.USE_OLLAMA:
                    answer = await self._call_ollama(messages)
                else:
                    answer = await self._call_openai(messages)
                t.set_output(answer)
            except Exception as e:
                logger.error("LLM call failed", error=str(e), provider=provider)
                answer = (
                    f"⚠️ AI model error ({provider}): {str(e)[:200]}\n\n"
                    f"If using OpenAI, check your API key has credits. "
                    f"If using Ollama, make sure it's running: `ollama serve`"
                )
                t.set_output(answer)

        sources = [
            {
                "document_id": c["document_id"],
                "document_title": c["document_title"],
                "page_number": c["page_number"],
                "chunk_text": c["chunk_text"][:300] + ("..." if len(c["chunk_text"]) > 300 else ""),
                "relevance_score": c["relevance_score"],
            }
            for c in retrieved
        ]

        return {"answer": answer, "sources": sources}

    async def _call_openai(self, messages: List[dict]) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
        )
        return response.choices[0].message.content

    async def _call_ollama(self, messages: List[dict]) -> str:
        import ollama
        import asyncio
        loop = asyncio.get_event_loop()

        def _sync_call():
            client = ollama.Client(host=settings.OLLAMA_BASE_URL)
            response = client.chat(model=settings.OLLAMA_MODEL, messages=messages)
            return response["message"]["content"]

        return await loop.run_in_executor(None, _sync_call)


rag_service = RAGService()
