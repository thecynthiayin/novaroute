from collections import OrderedDict
from hashlib import sha256
from threading import RLock

import numpy as np

from app.core.config import settings


class EmbeddingUnavailable(Exception):
    pass


class Embeddings:
    def __init__(self):
        self.model = None
        self.state = "not_loaded"
        self.cache = OrderedDict()
        self.lock = RLock()

    def load(self):
        with self.lock:
            if self.model is not None:
                return self.model
            try:
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(
                    settings().embedding_model, cache_folder=str(settings().embedding_cache_dir), device="cpu"
                )
                self.state = "ready"
                return self.model
            except Exception:
                self.state = "unavailable"
                raise EmbeddingUnavailable(
                    "Local recommendation model unavailable. Run the model warmup command; browsing and profile editing remain available."
                ) from None

    def encode(self, text):
        text = " ".join(text.split())
        key = (settings().embedding_model, sha256(text.encode()).hexdigest())
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            model = self.load()
            # Use actual tokenizer IDs to avoid accidental truncation at the model boundary.
            tokens = model.tokenizer.encode(text, add_special_tokens=False)
            width = max(16, model.max_seq_length - 2)
            chunks = [
                model.tokenizer.decode(tokens[i : i + width])
                for i in range(0, min(len(tokens), width * 16), width)
            ] or [""]
            vectors = model.encode(chunks, normalize_embeddings=True, convert_to_numpy=True)
            weights = np.ones(len(chunks))
            weights[0] = 2  # Structured fields appear first.
            vector = np.average(vectors, axis=0, weights=weights)
            vector = vector / max(float(np.linalg.norm(vector)), 1e-12)
            self.cache[key] = vector
            while len(self.cache) > 2048:
                self.cache.popitem(last=False)
            return vector

    def invalidate(self):
        with self.lock:
            self.cache.clear()


embeddings = Embeddings()


def profile_text(profile):
    skills = profile.extracted_skills or []
    coursework = profile.coursework or []
    projects = profile.projects or []
    proj_texts = []
    for p in projects:
        if isinstance(p, dict):
            t = p.get("title") or ""
            techs = ", ".join(p.get("technologies") or [])
            d = p.get("description") or ""
            proj_texts.append(f"{t} {techs} {d}".strip())
        elif isinstance(p, str):
            proj_texts.append(p)
    return (
        "Skills: "
        + ", ".join(skills)
        + ". Coursework: "
        + ", ".join(coursework)
        + ". Projects: "
        + "; ".join(proj_texts)
    )


def listing_text(listing):
    skills = listing.required_skills or []
    title = listing.title or ""
    desc = listing.description or ""
    return "Skills: " + ", ".join(skills) + ". " + title + ". " + desc


def rank(query_vector, candidates, threshold, limit):
    scored = []
    for identifier, vector in candidates:
        score = float(
            np.dot(query_vector, vector)
            / max(float(np.linalg.norm(query_vector) * np.linalg.norm(vector)), 1e-12)
        )
        if score > threshold:
            scored.append((identifier, score))
    return sorted(scored, key=lambda item: (-item[1], item[0]))[:limit]
