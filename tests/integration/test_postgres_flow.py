"""Integration tests for PostgreSQL flow."""

from unittest.mock import MagicMock, patch

import pytest

from samvaad.pipeline.retrieval.query import rag_query_pipeline


@pytest.fixture
def mock_db_for_ingestion():
    """Mock DBService for ingestion tests."""
    with patch("samvaad.pipeline.ingestion.ingestion.DBService") as mock_service:
        mock_service.check_content_exists.return_value = False
        mock_service.get_existing_chunk_hashes.return_value = set()
        mock_service.add_smart_dedup_content.return_value = {
            "status": "created",
            "file_id": "test_id",
        }
        yield mock_service


@pytest.fixture
def mock_embedding():
    """Mock embedding generation."""
    with patch("samvaad.pipeline.ingestion.ingestion.generate_embeddings") as mock_embed:
        # Return embeddings with same length as input
        mock_embed.side_effect = lambda chunks: [[0.1] * 1024 for _ in chunks]
        yield mock_embed


@pytest.fixture
def mock_parse_file():
    """Mock file parsing to avoid external API calls."""
    with patch("samvaad.pipeline.ingestion.ingestion.parse_file") as mock_parse:
        # Return mock pages structure
        mock_parse.return_value = (
            [
                {
                    "page": 1,
                    "items": [
                        {"type": "text", "value": "Test content page 1", "md": "Test content page 1"},
                        {"type": "text", "value": "More test content", "md": "More test content"},
                    ],
                }
            ],
            None,  # No error
        )
        yield mock_parse


def test_ingestion_flow_mocks(mock_db_for_ingestion, mock_embedding, mock_parse_file):
    """
    Test the ingestion pipeline logic with mocked DB, Embeddings, and Parsing.
    This ensures the pipeline orchestration is correct without needing a real DB or external APIs.
    """
    from samvaad.pipeline.ingestion.ingestion import ingest_file_pipeline_with_progress

    filename = "test_doc.txt"
    content = b"Content of the test document. " * 20
    content_type = "text/plain"

    result = ingest_file_pipeline_with_progress(filename, content_type, content)

    assert result["error"] is None
    assert result["num_chunks"] > 0

    # Verify DB Service was called
    mock_db_for_ingestion.check_content_exists.assert_called_once()
    mock_db_for_ingestion.add_smart_dedup_content.assert_called_once()

    # Verify parse_file was called
    mock_parse_file.assert_called_once_with(filename, content_type, content)


@patch("samvaad.pipeline.retrieval.query.DBService")
@patch("samvaad.pipeline.retrieval.query.embed_query")
@patch("samvaad.pipeline.retrieval.query.rerank_documents")
@patch("samvaad.pipeline.retrieval.query.generate_answer_with_groq")
def test_retrieval_flow_mocks(mock_gen, mock_rerank, mock_embed, mock_db):
    """
    Test the retrieval pipeline logic with mocked DB.
    """
    # Setup mocks
    mock_embed.return_value = [0.1] * 1024

    mock_db.search_similar_chunks.return_value = [
        {"id": "1", "document": "chunk content", "metadata": {"filename": "test.txt"}, "distance": 0.1}
    ]

    # Mock rerank result
    mock_rerank_res = MagicMock()
    result_item = MagicMock()
    result_item.index = 0
    result_item.relevance_score = 0.9
    mock_rerank_res.results = [result_item]
    mock_rerank.return_value = mock_rerank_res

    mock_gen.return_value = "Test Answer"

    # Run
    result = rag_query_pipeline("test query")

    assert result["success"] is True
    assert result["answer"] == "Test Answer"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["filename"] == "test.txt"
