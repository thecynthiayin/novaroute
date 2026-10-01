from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.simple_rag import simple_rag_query

router = APIRouter(tags=["Simple RAG"])


class SimpleRAGRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500, description="Question about internships")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of similar internships to retrieve")


class SimpleRAGResponse(BaseModel):
    answer: str
    sources: list[dict]
    num_results: int


@router.post("/simple-rag/query", response_model=SimpleRAGResponse)
def query_simple_rag(request: SimpleRAGRequest) -> dict:
    """Answer questions about internships using simple embedding search."""
    result = simple_rag_query(request.question, request.top_k)
    return result
