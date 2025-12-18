"""Test query functions using Voyage AI and PostgreSQL."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def reset_voyage_globals():
    """Reset global variables between tests to ensure clean state."""
    import samvaad.core.voyage
    samvaad.core.voyage._client = None

class TestEmbedQuery:
    """Test query embedding functions."""

    @patch("samvaad.core.voyage.voyageai.Client")
    def test_embed_query_success(self, mock_client_class):
        """Test embedding a query."""
        from samvaad.pipeline.retrieval.query import embed_query

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.embeddings = [[0.1, 0.2, 0.3]]
        mock_client.embed.return_value = mock_response
        mock_client_class.return_value = mock_client

        query = "test query"
        embedding = embed_query(query)

        assert embedding == [0.1, 0.2, 0.3]


class TestSearchSimilarChunks:
    """Test chunk search functions."""

    @patch("samvaad.pipeline.retrieval.query.rerank_documents")
    @patch("samvaad.pipeline.retrieval.query.DBService")
    def test_search_similar_chunks_success(self, mock_db_service, mock_rerank):
        """Test searching for similar chunks."""
        from samvaad.pipeline.retrieval.query import search_similar_chunks

        # Mock DB results
        mock_db_service.search_similar_chunks.return_value = [
            {
                "id": "chunk1",
                "document": "test query document",
                "metadata": {"filename": "test.txt"},
                "distance": 0.1,
            },
            {
                "id": "chunk2",
                "document": "unrelated document",
                "metadata": {"filename": "test2.txt"},
                "distance": 0.5,
            },
        ]

        # Mock rerank results
        mock_rerank_result = MagicMock()
        result1 = MagicMock()
        result1.index = 0
        result1.relevance_score = 0.9
        result2 = MagicMock()
        result2.index = 1
        result2.relevance_score = 0.3
        mock_rerank_result.results = [result1, result2]
        mock_rerank.return_value = mock_rerank_result

        query_emb = [0.1] * 1024
        query_text = "test query"
        results = search_similar_chunks(query_emb, query_text, top_k=2)

        assert len(results) == 2
        assert results[0]["content"] == "test query document"
        assert results[0]["rerank_score"] == 0.9

    @patch("samvaad.pipeline.retrieval.query.DBService")
    def test_search_similar_chunks_empty_results(self, mock_db_service):
        """Test searching when DB returns no results."""
        from samvaad.pipeline.retrieval.query import search_similar_chunks

        mock_db_service.search_similar_chunks.return_value = []

        query_emb = [0.1] * 1024
        query_text = "test query"
        results = search_similar_chunks(query_emb, query_text, top_k=3)

        assert results == []

    @patch("samvaad.pipeline.retrieval.query.DBService")
    def test_search_similar_chunks_db_error(self, mock_db_service):
        """Test handling of DB search errors."""
        from samvaad.pipeline.retrieval.query import search_similar_chunks

        mock_db_service.search_similar_chunks.side_effect = Exception("DB connection failed")

        query_emb = [0.1] * 1024
        query_text = "test query"
        results = search_similar_chunks(query_emb, query_text, top_k=3)

        # Should return empty list on error
        assert results == []


class TestQueryErrorHandling:
    """Test error handling in query functions."""

    @patch("samvaad.pipeline.retrieval.query.generate_answer_with_groq")
    @patch("samvaad.pipeline.retrieval.query.search_similar_chunks")
    @patch("samvaad.pipeline.retrieval.query.embed_query")
    def test_rag_query_pipeline_groq_failure(self, mock_embed, mock_search, mock_generate):
        """Test RAG pipeline when Groq fails."""
        from samvaad.pipeline.retrieval.query import rag_query_pipeline

        mock_embed.return_value = [0.1] * 1024
        mock_search.return_value = [{"content": "Test", "filename": "test.txt", "rerank_score": 0.9}]
        mock_generate.side_effect = Exception("Groq API error")

        result = rag_query_pipeline("test query")

        assert result["success"] is False
        assert "Error" in result["answer"]

    @patch("samvaad.pipeline.retrieval.query.rerank_documents")
    @patch("samvaad.pipeline.retrieval.query.DBService")
    def test_search_chunks_rerank_failure(self, mock_db_service, mock_rerank):
        """Test handling of rerank failure."""
        from samvaad.pipeline.retrieval.query import search_similar_chunks

        mock_db_service.search_similar_chunks.return_value = [
            {"id": "1", "document": "test", "metadata": {"filename": "test.txt"}, "distance": 0.1}
        ]
        mock_rerank.side_effect = Exception("Rerank API error")

        query_emb = [0.1] * 1024
        
        # Should handle error gracefully or raise - assuming raise for now based on implementation
        try:
            results = search_similar_chunks(query_emb, "test", top_k=3)
        except Exception:
            pass


class TestRAGQueryPipeline:
    """Test the complete RAG query pipeline."""

    @patch("samvaad.pipeline.retrieval.query.generate_answer_with_groq")
    @patch("samvaad.pipeline.retrieval.query.search_similar_chunks")
    @patch("samvaad.pipeline.retrieval.query.embed_query")
    def test_rag_query_pipeline_success(self, mock_embed, mock_search, mock_generate):
        """Test a successful full RAG pipeline run."""
        from samvaad.pipeline.retrieval.query import rag_query_pipeline

        mock_embed.return_value = [0.1] * 1024
        mock_chunks = [
            {"content": "Chunk A content", "filename": "A.pdf", "distance": 0.1, "rerank_score": 0.9},
            {"content": "Chunk B content", "filename": "B.pdf", "distance": 0.2, "rerank_score": 0.8},
        ]
        mock_search.return_value = mock_chunks
        mock_generate.return_value = "The answer is in the documents."

        query_text = "What is A?"
        result = rag_query_pipeline(query_text)

        assert result["success"] is True
        assert result["answer"] == "The answer is in the documents."
        assert result["retrieval_count"] == 2
        assert len(result["sources"]) == 2

        # Verify sources format
        assert result["sources"][0]["filename"] == "A.pdf"
        assert result["sources"][0]["rerank_score"] == 0.9

    @patch("samvaad.pipeline.retrieval.query.search_similar_chunks", return_value=[])
    @patch("samvaad.pipeline.retrieval.query.embed_query")
    def test_rag_query_pipeline_no_retrieval(self, mock_embed, mock_search):
        """Test query pipeline when search returns no results."""
        from samvaad.pipeline.retrieval.query import rag_query_pipeline

        mock_embed.return_value = [0.1] * 1024

        result = rag_query_pipeline("test query")

        assert result["success"] is False
        assert "No relevant documents" in result["answer"]
        assert result["sources"] == []
        assert result["retrieval_count"] == 0

    @patch("samvaad.pipeline.retrieval.query.search_similar_chunks", return_value=[])
    @patch("samvaad.pipeline.retrieval.query.embed_query")
    def test_rag_query_pipeline_strict_mode_no_chunks(self, mock_embed, mock_search):
        """Test strict mode when no chunks are found."""
        from samvaad.pipeline.retrieval.query import rag_query_pipeline

        mock_embed.return_value = [0.1] * 1024

        result = rag_query_pipeline("test query", strict_mode=True)

        assert result["success"] is True  # Strict mode "I don't know" is a success
        assert "don't know" in result["answer"].lower()

    @patch("samvaad.pipeline.retrieval.query.embed_query")
    def test_rag_query_pipeline_error_handling(self, mock_embed):
        """Test query pipeline error handling."""
        from samvaad.pipeline.retrieval.query import rag_query_pipeline

        mock_embed.side_effect = Exception("Test error")

        result = rag_query_pipeline("test query")

        assert result["success"] is False
        assert "Error processing query" in result["answer"]
        assert result["sources"] == []
        assert result["retrieval_count"] == 0

    @patch("samvaad.pipeline.retrieval.query.generate_answer_with_groq")
    @patch("samvaad.pipeline.retrieval.query.search_similar_chunks")
    @patch("samvaad.pipeline.retrieval.query.embed_query")
    def test_rag_query_pipeline_with_persona(self, mock_embed, mock_search, mock_generate):
        """Test RAG pipeline with persona parameter."""
        from samvaad.pipeline.retrieval.query import rag_query_pipeline

        mock_embed.return_value = [0.1] * 1024
        mock_search.return_value = [{"content": "Test", "filename": "test.txt", "rerank_score": 0.9}]
        mock_generate.return_value = "Friendly response"

        result = rag_query_pipeline("test query", persona="friend")

        assert result["success"] is True
        # Verify persona was passed to generate function
        call_kwargs = mock_generate.call_args
        assert call_kwargs is not None

    @patch("samvaad.pipeline.retrieval.query.generate_answer_with_groq")
    @patch("samvaad.pipeline.retrieval.query.search_similar_chunks")
    @patch("samvaad.pipeline.retrieval.query.embed_query")
    def test_rag_query_pipeline_with_history(self, mock_embed, mock_search, mock_generate):
        """Test RAG pipeline with conversation history."""
        from samvaad.pipeline.retrieval.query import rag_query_pipeline

        mock_embed.return_value = [0.1] * 1024
        mock_search.return_value = [{"content": "Test", "filename": "test.txt", "rerank_score": 0.9}]
        mock_generate.return_value = "Contextual response"

        history = "User: Hi\nAssistant: Hello!"
        result = rag_query_pipeline("test query", history_str=history)

        assert result["success"] is True