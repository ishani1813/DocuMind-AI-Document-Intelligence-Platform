"""ChromaDB vector store with local fallback."""

import structlog
import chromadb

from app.core.config import settings

logger = structlog.get_logger()

_chroma_client = None
_collection = None


async def init_vector_store():
    global _chroma_client, _collection

    logger.info("Initializing ChromaDB", host=settings.CHROMA_HOST)

    # Try HTTP client first (production)
    try:
        client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=int(settings.CHROMA_PORT),
        )
        client.heartbeat()
        _chroma_client = client
        logger.info("ChromaDB HTTP client connected")
    except Exception as e:
        logger.warning("ChromaDB HTTP failed, using local", error=str(e))
        try:
            _chroma_client = chromadb.PersistentClient(path="/app/chroma_data")
            logger.info("ChromaDB local persistent client ready")
        except Exception as e2:
            logger.warning("ChromaDB persistent failed, using ephemeral", error=str(e2))
            _chroma_client = chromadb.EphemeralClient()
            logger.info("ChromaDB ephemeral client ready")

    # Create collection
    try:
        _collection = _chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection ready", name=settings.CHROMA_COLLECTION_NAME)
    except Exception as e:
        logger.error("ChromaDB collection creation failed", error=str(e))


def get_chroma_client():
    if _chroma_client is None:
        raise RuntimeError("ChromaDB not initialized")
    return _chroma_client


def get_chroma_collection():
    if _collection is None:
        raise RuntimeError("ChromaDB collection not initialized")
    return _collection
