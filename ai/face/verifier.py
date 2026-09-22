"""التحقق من تطابق الوجهين"""
import numpy as np
from numpy.linalg import norm
from ai.face.config import DEFAULT_THRESHOLD


def cosine_similarity(emb1, emb2):
    return float(np.dot(emb1, emb2) / (norm(emb1) * norm(emb2)))


def verify_faces(face1, face2, threshold=DEFAULT_THRESHOLD):
    """التحقق من تطابق وجهين"""
    emb1 = face1.normed_embedding
    emb2 = face2.normed_embedding
    similarity = cosine_similarity(emb1, emb2)
    return {
        'matched': bool(similarity >= threshold),
        'similarity': float(similarity),
        'threshold': float(threshold),
        'distance': float(1.0 - similarity),
    }