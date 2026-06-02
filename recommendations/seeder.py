import logging

from recommendations.anime_store import AnimeStore
from recommendations.embed import EmbeddingGenerator
from recommendations.qdrant_store import QdrantStore

from qdrant_client.models import PointStruct

# Configure logging
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class QdrantSeeder:
    def __init__(self) -> None:
        self.anime_store = AnimeStore()
        self.embedgen = EmbeddingGenerator(parallel=16, batch_size=256)
        self.qdrant_store = QdrantStore()

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
        df = self.anime_store.df
        alr_uploaded = self.qdrant_store.get_uploaded_point_ids(df.shape[0])
        all_ids = set(df["id"])
        to_seed = all_ids - alr_uploaded
        logger.info(f"Starting seeding of {len(to_seed)} documents.")
        if not to_seed:
            logger.info("No new documents to seed.")
            return

        df_to_seed = df[df["id"].isin(to_seed)]
        rows = df_to_seed.to_dict(orient="records")
        batch_size = max(1, self.embedgen.batch_size)
        total = len(rows)
        total_batches = (total + batch_size - 1) // batch_size

        for batch_idx, batch in enumerate(
            self._iter_batches(rows, batch_size), start=1
        ):
            vectors = self.embedgen.embed_anime_rows(batch)
            points = []
            for row, vector in zip(batch, vectors):
                points.append(
                    PointStruct(
                        id=int(row["id"]),
                        vector=list(vector),
                        payload=self._row_to_payload(row),
                    )
                )
            self.qdrant_store.upload_points(points)
            uploaded = min(batch_idx * batch_size, total)
            logger.info(
                "Uploaded %s/%s points (%s/%s batches).",
                uploaded,
                total,
                batch_idx,
                total_batches,
            )


def main():
    qseeder = QdrantSeeder()
    qseeder.seed()
    qseeder.qdrant_store.enable_indexing()


if __name__ == "__main__":
    main()
