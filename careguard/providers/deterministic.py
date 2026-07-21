class DeterministicExtractiveProvider:
    """No-key provider that returns an approved excerpt without generative inference."""

    provider_id = "deterministic-local"
    model_id = "extractive-v1"

    def answer(self, excerpt: str, source_id: str) -> str:
        cleaned = " ".join(excerpt.split())
        return f"{cleaned} [Source: {source_id}]"

