import requests

# Test simple RAG query
print("Testing Simple RAG query...")
response = requests.post(
    "http://127.0.0.1:8000/api/simple-rag/query",
    json={
        "question": "What skills are required for data science internships?",
        "top_k": 3
    }
)
print("Status:", response.status_code)
print(response.json())
