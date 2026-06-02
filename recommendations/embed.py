from fastembed import TextEmbedding


class EmbeddingGenerator:
    def __init__(self, parallel: int = 8, batch_size: int = 128) -> None:
        self.parallel = parallel
        self.batch_size = batch_size
        self.model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", lazy_load=True)

    def embed_docs(self, docs: list[str]):
        return list(
            self.model.embed(docs, batch_size=self.batch_size, parallel=self.parallel)
        )

    def embed_anime_rows(self, rows: list[dict]):
        return self.embed_docs([self._row_to_doc(r) for r in rows])

    def embed_anime_row(self, row: dict):
        return self.embed_anime_rows([row])

    @staticmethod
    def _row_to_doc(row: dict) -> str:
        parts = [
            ("Title", row.get("title", "")),
            ("Alt title (EN)", row.get("alt_title_en", "")),
            ("Alt title (JP)", row.get("alt_title_jp", "")),
            ("Synopsis", row.get("synopsis", "")),
            ("Genres", row.get("genres", "")),
            ("Themes", row.get("themes", "")),
            ("Demographics", row.get("demographics", "")),
            ("Studios", row.get("studios", "")),
            ("Type", row.get("media_type", "")),
            ("Status", row.get("status", "")),
            ("Rating", row.get("rating", "")),
        ]
        lines = [f"{label}: {value}" for label, value in parts if value]
        return "\n".join(lines)


if __name__ == "__main__":
    print(EmbeddingGenerator().model.embedding_size)
