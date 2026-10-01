# Simple RAG Implementation

This is a **much simpler RAG** that uses your existing embeddings system - no FAISS, no document processing, no complex indexing needed!

## What It Does

- Answers questions about internships by searching your database
- Uses the same MiniLM embeddings you already have for recommendations
- Finds similar internships based on your question
- Works in both demo mode (simple rules) and live mode (with OpenRouter)

## How to Use

### 1. Restart the FastAPI Server

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1:8000
```

### 2. Test It

Run the test script:

```powershell
python test_rag_api.py
```

Or use PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/simple-rag/query" -Body '{"question": "What skills are required for data science internships?", "top_k": 3}' -ContentType "application/json"
```

### 3. API Endpoint

**POST** `/api/simple-rag/query`

Request body:
```json
{
  "question": "What skills are required for data science internships?",
  "top_k": 3
}
```

Response:
```json
{
  "answer": "Based on the available internships, Python is commonly required...",
  "sources": [
    {
      "title": "Data Engineer",
      "skills": ["Python", "SQL"],
      "similarity": 0.85
    }
  ],
  "num_results": 3
}
```

## What's Different from Complex RAG

| Feature | Complex RAG | Simple RAG |
|---------|-------------|------------|
| Vector Store | FAISS/ChromaDB | None (in-memory) |
| Document Processing | Chunking, PDF parsing | None |
| Indexing | Required | Not needed |
| Configuration | Many settings | None |
| Dependencies | FAISS, rank-bm25 | None (uses existing) |
| Performance | Slower startup | Fast startup |
| Memory | Higher | Lower |

## How It Works

1. Takes your question
2. Encodes it with MiniLM (already loaded)
3. Computes similarity with all active internships
4. Returns top 3 most similar internships
5. Generates answer using LLM or demo rules

That's it! No setup, no indexing, no configuration. Just works with what you already have.
