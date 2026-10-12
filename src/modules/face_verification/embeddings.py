import numpy as np


class EmbeddingExtractor:
    def extract(self, face) -> np.ndarray | None:
        if face is None:
            return None
        emb = getattr(face, "normed_embedding", None)
        if emb is None:
            emb = getattr(face, "embedding", None)
        if emb is None:
            return None
        return np.asarray(emb, dtype=np.float32)