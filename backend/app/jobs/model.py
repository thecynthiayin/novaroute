import argparse

from app.services.embeddings import embeddings
from app.services.recommendations import evaluate_alerts

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry-matches", action="store_true")
    args = parser.parse_args()
    embeddings.load()
    vector = embeddings.encode("Python SQL technical internship")
    print(f"Real local embedding ready: {len(vector)} dimensions")
    if args.retry_matches:
        evaluate_alerts()
        print("High-match evaluations completed")
