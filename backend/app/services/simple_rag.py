from typing import Dict, List

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Internship
from app.services.embeddings import embeddings, listing_text
from app.services.openrouter import AIError, structured


def simple_rag_query(question: str, top_k: int = 3) -> Dict:
    """Simple RAG: search internships by embedding similarity and answer questions."""
    try:
        with SessionLocal() as db:
            listings = list(
                db.scalars(
                    select(Internship).where(
                        Internship.status == "active",
                        Internship.deleted_at.is_(None),
                    )
                )
            )

        if not listings:
            return {
                "answer": "No active internships found in the database.",
                "sources": [],
            }

        # Encode the question
        question_vector = embeddings.encode(question)

        # Compute similarity with all listings
        scored = []
        for listing in listings:
            listing_vector = embeddings.encode(listing_text(listing))
            similarity = float(
                (question_vector @ listing_vector)
                / (question_vector @ question_vector) ** 0.5
                / (listing_vector @ listing_vector) ** 0.5
            )
            scored.append((listing, similarity))

        # Sort by similarity and get top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        top_listings = scored[:top_k]

        # Prepare context from top listings
        context_parts = []
        for listing, score in top_listings:
            context_parts.append(
                f"Internship: {listing.title}\n"
                f"Skills: {', '.join(listing.required_skills)}\n"
                f"Description: {listing.description}\n"
                f"Similarity: {score:.2f}"
            )
        context = "\n\n".join(context_parts)

        # Generate answer
        answer = generate_simple_answer(question, context)

        sources = [
            {
                "title": listing.title,
                "skills": listing.required_skills,
                "similarity": round(score, 2),
            }
            for listing, score in top_listings
        ]

        return {
            "answer": answer,
            "sources": sources,
            "num_results": len(top_listings),
        }
    except Exception as e:
        return {
            "answer": f"Error processing query: {str(e)}",
            "sources": [],
        }


def generate_simple_answer(question: str, context: str) -> str:
    """Generate answer using LLM or demo mode."""
    from pydantic import BaseModel

    class SimpleAnswer(BaseModel):
        answer: str

    task = (
        "You are a helpful assistant for an internship platform. "
        "Answer the user's question based ONLY on the provided internship listings. "
        "If the context doesn't contain the answer, say so clearly. "
        "Be concise and factual."
    )

    data = {"question": question, "context": context}

    try:
        if settings().ai_mode == "demo":
            return demo_simple_answer(question, context)

        response = structured(SimpleAnswer, task, data)
        return response.answer
    except AIError:
        return demo_simple_answer(question, context)


def demo_simple_answer(question: str, context: str) -> str:
    """Demo mode: simple pattern matching."""
    question_lower = question.lower()

    if "skill" in question_lower or "require" in question_lower:
        if "python" in context.lower():
            return "Based on the available internships, Python is commonly required for data science, software engineering, and machine learning roles."
        elif "sql" in context.lower():
            return "The listings indicate SQL is frequently required for database, data engineering, and data science positions."
        else:
            return "The internships require various technical skills. Please specify which skill you're interested in."

    if "internship" in question_lower or "role" in question_lower:
        return f"Found {context.count('Internship:')} active internships including software engineering, data science, and database roles. Check the sources for specific requirements."

    return f"Based on the indexed internships: {context[:200]}... (Demo mode - enable live mode with OpenRouter API key for full AI responses)"
