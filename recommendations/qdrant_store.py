import logging
import os

from qdrant_client import QdrantClient, models

from recommendations.embed import EmbeddingGenerator

_EMBEDDING_SIZE = EmbeddingGenerator().model.embedding_size

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
QDRANT_COLLECTION = "anime"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class QdrantStore:
    def __init__(self) -> None:
        self.client = self.create_client()
        self.ensure_collection()

    @staticmethod
    def create_client() -> QdrantClient:
        logger.info(f"Creating Qdrant client: {QDRANT_URL}")
        client = QdrantClient(url=QDRANT_URL)
        try:
            client.get_collections()
        except Exception as exc:
            # fail fast if Qdrant is unavailable.
            logger.exception("Qdrant connection failed")
            raise RuntimeError("Failed to connect to Qdrant") from exc
        logger.info("Qdrant connection ok")
        return client

    def ensure_collection(self):
        if self.client.collection_exists(QDRANT_COLLECTION):
            logger.info(
                f"Collection {QDRANT_COLLECTION} already exists, skipping creation."
            )
            return

        logger.info(f"Creating collection {QDRANT_COLLECTION}.")
        self.client.create_collection(
            QDRANT_COLLECTION,
            models.VectorParams(
                size=_EMBEDDING_SIZE,
                distance=models.Distance.COSINE,
                hnsw_config=models.HnswConfigDiff(m=0),
                on_disk=True,
                quantization_config=models.TurboQuantization(
                    turbo=models.TurboQuantQuantizationConfig(
                        always_ram=True,
                    ),
                ),
            ),
            shard_number=2,
        )

    def enable_indexing(self):
        self.client.update_collection(
            QDRANT_COLLECTION,
            hnsw_config=models.HnswConfigDiff(m=16),
        )

    def get_uploaded_point_ids(self, limit: int):
        res = self.client.scroll(
            QDRANT_COLLECTION,
            with_payload=False,
            with_vectors=False,
            limit=limit,
        )
        ids = {r.id for r in res[0]}
        return ids

    def upload_points(self, points: list[models.PointStruct]):
        self.client.upload_points(
            QDRANT_COLLECTION, points=points, wait=False, parallel=4
        )

    def similarity_search(self, vector, limit=10):
        return self.client.query_points(
            QDRANT_COLLECTION, query=vector, with_payload=True, limit=limit
        )
