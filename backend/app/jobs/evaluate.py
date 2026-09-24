"""Reproducible small-sample ranking comparison, not a measured accuracy claim."""

import argparse
import csv
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from app.services.embeddings import embeddings, listing_text, profile_text
from app.services.skills import normalize

ROOT = Path(__file__).resolve().parents[3]


def metrics(order, relevant, k=5):
    precision = sum(identifier in relevant for identifier in order[:k]) / k
    reciprocal = next((1 / (i + 1) for i, identifier in enumerate(order) if identifier in relevant), 0.0)
    return {"precision_at_5": precision, "reciprocal_rank": reciprocal}


def evaluate(labels_path):
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    if not labels["profiles"]:
        raise ValueError("No reviewed profiles supplied; independent evaluation has not been performed")
    with (ROOT / "database/data/synthetic-internships.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    vectors = {
        r["source_id"]: embeddings.encode(
            listing_text(
                SimpleNamespace(
                    title=r["internship_title"],
                    required_skills=r["skills"].split("|"),
                    description=r["description"],
                )
            )
        )
        for r in rows
    }
    results = []
    for p in labels["profiles"]:
        vector = embeddings.encode(
            profile_text(
                SimpleNamespace(
                    extracted_skills=p["skills"], coursework=p["coursework"], projects=p["projects"]
                )
            )
        )
        scores = {key: float(np.dot(vector, v)) for key, v in vectors.items()}
        ranked = sorted(scores, key=lambda key: (-scores[key], key))
        known = {x.lower() for x in normalize(p["skills"])}
        overlap = {
            r["source_id"]: len(known.intersection(s.lower() for s in normalize(r["skills"].split("|"))))
            / max(1, len(r["skills"].split("|")))
            for r in rows
        }
        baseline = sorted(overlap, key=lambda key: (-overlap[key], key))
        results.append(
            {
                "profile": p["id"],
                "embedding": metrics(ranked, p["relevant"]),
                "keyword_baseline": metrics(baseline, p["relevant"]),
                "embedding_top5": ranked[:5],
                "strictly_above_0_80": sum(s > 0.8 for s in scores.values()),
            }
        )
    return {
        "label_status": labels["label_status"],
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "candidates": len(rows),
        "profiles": len(results),
        "embedding": {
            "precision_at_5": float(np.mean([r["embedding"]["precision_at_5"] for r in results])),
            "mrr": float(np.mean([r["embedding"]["reciprocal_rank"] for r in results])),
        },
        "keyword_baseline": {
            "precision_at_5": float(np.mean([r["keyword_baseline"]["precision_at_5"] for r in results])),
            "mrr": float(np.mean([r["keyword_baseline"]["reciprocal_rank"] for r in results])),
        },
        "per_profile": results,
        "limitations": "Three synthetic profiles and proposed labels; no independent validation, tuning, accuracy or hiring-outcome claim.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, default=ROOT / "docs/evaluation/proposed-labels.json")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evaluation/results.json")
    args = parser.parse_args()
    result = evaluate(args.labels)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
