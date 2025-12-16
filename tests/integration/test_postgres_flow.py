import pytest
from unittest.mock import MagicMock, patch
from samvaad.db.service import DBService
from samvaad.pipeline.ingestion.ingestion import ingest_file_pipeline_with_progress
from samvaad.pipeline.retrieval.query import rag_query_pipeline

@pytest.fixture
def mock_db_service():
    with patch("samvaad.pipeline.ingestion.ingestion.DBService") as mock_service:
        # Setup mock return values
        mock_service.file_exists.return_value = False
        mock_service.add_file_and_chunks.return_value = {
            "status": "created",
            "file_id": "test_id",
            "chunks_added": 5
        }
        yield mock_service

@pytest.fixture
def mock_embedding():
    with patch("samvaad.pipeline.ingestion.ingestion.generate_embeddings") as mock_embed:
        # Return dummy embeddings (list of lists of floats)
        # 5 chunks, 1024 dim
        mock_embed.return_value = [[0.1] * 1024] * 5
        yield mock_embed

def test_ingestion_flow_mocks(mock_db_service, mock_embedding):
    """
    Test the ingestion pipeline logic with mocked DB and Embeddings.
    This ensures the pipeline orchestration is correct without needing a real DB.
    """
    filename = "test_doc.txt"
    content = b"Content of the test document. " * 20 # Make it long enough to chunk
    content_type = "text/plain"
    
    result = ingest_file_pipeline_with_progress(filename, content_type, content)
    
    assert result["error"] is None
    assert result["num_chunks"] > 0
    assert result["new_chunks_embedded"] == 5
    
    # Verify DB Service was called
    mock_db_service.file_exists.assert_called_once()
    mock_db_service.add_file_and_chunks.assert_called_once()

@patch("samvaad.pipeline.retrieval.query.DBService")
@patch("samvaad.pipeline.retrieval.query.embed_query")
@patch("samvaad.pipeline.retrieval.query._rerank_with_backoff")
@patch("samvaad.pipeline.retrieval.query.generate_answer_with_groq")
def test_retrieval_flow_mocks(mock_gen, mock_rerank, mock_embed, mock_db):
    """
    Test the retrieval pipeline logic with mocked DB.
    """
    # Setup mocks
    mock_embed.return_value = [0.1] * 1024
    
    mock_db.search_similar_chunks.return_value = [
        {
            "id": "1", 
            "document": "chunk content", 
            "metadata": {"filename": "test.txt"},
            "distance": 0.1
        }
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
