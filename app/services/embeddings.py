import logging

from app.core import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None  # Remove type hint here if it causes issues or use Any
        self.embedding_dimension = 384
        logger.info(f"Initializing EmbeddingService with model: {model_name}")

    def _ensure_model_loaded(self):
        """Lazy load the model on first use to prevent circular imports"""
        if self.model is None:
            # LOCAL IMPORT: This prevents the crash during pytest discovery
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        self._ensure_model_loaded()

        try:
            # Generate embedding
            if not self.model:
                raise RuntimeError("Embedding model failed to load.")

            try:
                # 2. Linter now knows 'encode' exists
                embedding = self.model.encode(text, convert_to_numpy=True)
                return embedding.tolist()
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
                raise

            # Convert to list and return
            return embedding.tolist()

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
        self._ensure_model_loaded()

        if not texts:
            return []

        # 1. Type Guard: Narrow the type for the linter
        if not self.model:
            raise RuntimeError("Embedding model failed to load.")

        try:
            logger.info(f"Generating embeddings for {len(texts)} texts in batches of {batch_size}")

            # 2. Pyright/Ruff now knows this is safe
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )

            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        return self.embedding_dimension


# Global instance
# embedding_service = EmbeddingService(
#     model_name=getattr(settings, "EMBEDDING_MODEL", "all-MiniLM-L6-v2")
# )
