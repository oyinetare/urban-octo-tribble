import asyncio
import logging

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.embedding_dimension = 384
        logger.info(f"Initializing EmbeddingService with model: {model_name}")

    async def _ensure_model_loaded(self):
        """Asynchronously load the model using a separate thread to avoid blocking"""
        if self.model is None:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {self.model_name}")

            # Offload heavy CPU work to a thread so the event loop stays free
            self.model = await asyncio.to_thread(SentenceTransformer, self.model_name)

            logger.info("Embedding model loaded successfully")

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        try:
            if self.model is None:
                raise RuntimeError("Model not loaded. Call await _ensure_model_loaded() first.")
            return self.model.encode(text, convert_to_numpy=True).tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def embed_batch(
        self, texts: list[str], batch_size: int = 32, show_progress: bool = False
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batches

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            show_progress: Whether to show progress bar

        Returns:
            List of embedding vectors
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call await _ensure_model_loaded() first.")
        try:
            logger.info(f"Generating embeddings for {len(texts)} texts in batches of {batch_size}")

            return self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=True,
            ).tolist()

        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        return self.embedding_dimension
