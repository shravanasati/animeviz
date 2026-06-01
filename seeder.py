import logging
import os

from embed import EmbeddingGenerator

from pathlib import Path
import pandas as pd
from qdrant_client import QdrantClient, models

# Configure logging
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
QDRANT_COLLECTION = "anime"


def load_data():
    df = pd.read_csv(Path(__file__).parent / "anime_data_cleaned.csv")

    df["start_date"] = df["start_date"].fillna("")
    df["end_date"] = df["end_date"].fillna("")

    textcols = [
        "synopsis",
        "genres",
        "themes",
        "demographics",
        "studios",
        "related_anime",
        "alt_title_en",
        "alt_title_jp",
    ]
    for col in textcols:
        df[col] = df[col].fillna("")

    return df


class QdrantSeeder:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df
        self.client = self.create_client()
        self.embedgen = EmbeddingGenerator(parallel=16, batch_size=256)
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
                size=self.embedgen.model.embedding_size,
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

    def get_uploaded_point_ids(self):
        res = self.client.scroll(
            QDRANT_COLLECTION,
            with_payload=False,
            with_vectors=False,
            limit=self.df.shape[0],
        )
        ids = {r.id for r in res[0]}
        return ids

    @staticmethod
    def _row_to_payload(row: dict) -> dict:
        payload = dict(row)
        payload.pop("synopsis")
        return payload

    @staticmethod
    def _iter_batches(items: list, batch_size: int):
        for idx in range(0, len(items), batch_size):
            yield items[idx : idx + batch_size]

    def seed(self):
        alr_uploaded = self.get_uploaded_point_ids()
        all_ids = set(self.df["id"])
        to_seed = all_ids - alr_uploaded
        logger.info(f"Starting seeding of {len(to_seed)} documents.")
        if not to_seed:
            logger.info("No new documents to seed.")
            return

        df_to_seed = self.df[self.df["id"].isin(to_seed)]
        rows = df_to_seed.to_dict(orient="records")
        batch_size = max(1, self.embedgen.batch_size)
        total = len(rows)
        total_batches = (total + batch_size - 1) // batch_size

        for batch_idx, batch in enumerate(
            self._iter_batches(rows, batch_size), start=1
        ):
            vectors = self.embedgen.embed_rows(batch)
            points = []
            for row, vector in zip(batch, vectors):
                points.append(
                    models.PointStruct(
                        id=int(row["id"]),
                        vector=list(vector),
                        payload=self._row_to_payload(row),
                    )
                )
            self.client.upload_points(
                QDRANT_COLLECTION, points=points, wait=False, parallel=4
            )
            uploaded = min(batch_idx * batch_size, total)
            logger.info(
                "Uploaded %s/%s points (%s/%s batches).",
                uploaded,
                total,
                batch_idx,
                total_batches,
            )


def main():
    df = load_data()
    qseeder = QdrantSeeder(df)
    qseeder.seed()


if __name__ == "__main__":
    main()
