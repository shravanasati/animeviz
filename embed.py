from fastembed import TextEmbedding


class EmbeddingGenerator:
    def __init__(self, parallel: int = 8, batch_size: int = 128) -> None:
        self.parallel = parallel
        self.batch_size = batch_size
        self.model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", lazy_load=True)

    def embed(self, docs: list[str]):
        return list(
            self.model.embed(docs, batch_size=self.batch_size, parallel=self.parallel)
        )


if __name__ == "__main__":
    print(EmbeddingGenerator().model.embedding_size)
