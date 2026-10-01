import pytest
from unittest.mock import Mock, patch

from app.services.simple_rag import simple_rag_query


class TestSimpleRAG:
    @patch("app.services.simple_rag.embeddings")
    @patch("app.services.simple_rag.SessionLocal")
    def test_simple_rag_query(self, mock_session, mock_embeddings):
        from app.models import Internship

        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_listing = Mock(spec=Internship)
        mock_listing.title = "Data Engineer"
        mock_listing.required_skills = ["Python", "SQL"]
        mock_listing.description = "Build data pipelines"
        mock_db.scalars.return_value.all.return_value = [mock_listing]

        mock_embeddings.encode.return_value = [0.1, 0.2, 0.3]

        result = simple_rag_query("What skills are needed?", top_k=3)
        assert "answer" in result
        assert "sources" in result

    @patch("app.services.simple_rag.embeddings")
    @patch("app.services.simple_rag.SessionLocal")
    def test_simple_rag_no_listings(self, mock_session, mock_embeddings):
        mock_db = Mock()
        mock_session.return_value.__enter__.return_value = mock_db
        mock_db.scalars.return_value.all.return_value = []

        result = simple_rag_query("What skills are needed?")
        assert "No active internships" in result["answer"]
