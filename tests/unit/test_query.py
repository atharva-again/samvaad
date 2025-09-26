import pytest
from unittest.mock import patch, MagicMock

# Import modules to test
from backend.pipeline.query import embed_query, search_similar_chunks, generate_answer_with_gemini, rag_query_pipeline


class TestQuery:
    """Test query functions."""

    @patch('backend.pipeline.query.get_embedding_model')
    def test_embed_query(self, mock_get_model):
        """Test embedding a query."""
        mock_model = MagicMock()
        # Mock numpy array with tolist() method
        mock_embeddings = MagicMock()
        mock_embeddings.tolist.return_value = [0.1, 0.2, 0.3]
        mock_model.encode.return_value = [mock_embeddings]  # Return list with one element
        mock_get_model.return_value = mock_model

        query = "test query"
        embedding = embed_query(query)

        assert embedding == [0.1, 0.2, 0.3]
        mock_model.encode.assert_called_once()

    @patch('backend.pipeline.query.BM25Okapi')
    @patch('backend.pipeline.query.collection')
    @patch('backend.pipeline.query.get_cross_encoder')
    @patch('backend.pipeline.query.get_embedding_model')
    def test_search_similar_chunks(self, mock_emb_model, mock_cross_encoder, mock_collection, mock_bm25):
        """Test searching for similar chunks."""
        # Mock BM25 to return predictable scores (higher for first document)
        mock_bm25_instance = MagicMock()
        mock_bm25_instance.get_scores.return_value = [2.0, 1.0]  # First doc scores higher
        mock_bm25.return_value = mock_bm25_instance
        
        # Mock embedding model
        mock_emb_model_inst = MagicMock()
        mock_emb_model_inst.encode.return_value = [[0.1] * 768]
        mock_emb_model.return_value = mock_emb_model_inst

        # Mock collection
        mock_collection.get.return_value = {
            "documents": ["test query document", "unrelated document"],
            "metadatas": [{"filename": "test.txt"}, {"filename": "test.txt"}]
        }
        mock_collection.query.return_value = {
            "documents": [["test query document"]],
            "metadatas": [[{"filename": "test.txt"}]],
            "distances": [[0.1]]
        }

        # Mock cross encoder
        mock_ce_inst = MagicMock()
        mock_ce_inst.predict.return_value = [0.9, 0.1]  # First candidate gets higher score
        mock_cross_encoder.return_value = mock_ce_inst

        query_emb = [0.1] * 768
        query_text = "test query"
        results = search_similar_chunks(query_emb, query_text, top_k=1)

        assert len(results) == 1
        assert results[0]['content'] == 'test query document'

    @patch('backend.pipeline.query.collection')
    def test_search_similar_chunks_no_results(self, mock_collection):
        """Test searching when collection.get returns no documents."""
        mock_collection.get.return_value = {
            "documents": [],
            "metadatas": []
        }
        
        query_emb = [0.1] * 768
        query_text = "test query"
        results = search_similar_chunks(query_emb, query_text, top_k=3)
        
        assert results == []

    @patch('backend.pipeline.query.embed_query')
    @patch('backend.pipeline.query.search_similar_chunks', return_value=[])
    def test_rag_query_pipeline_no_retrieval(self, mock_search, mock_embed_query):
        """Test query pipeline when search_similar_chunks returns no results."""
        mock_embed_query.return_value = [0.1] * 768

        result = rag_query_pipeline("test query")

        assert result['success'] == False
        assert "No relevant documents found" in result['answer']
        assert result['sources'] == []
        assert result['retrieval_count'] == 0
        mock_search.assert_called_once()  # Verify search was attempted

    @patch('backend.pipeline.query.embed_query')
    @patch('backend.pipeline.query.search_similar_chunks')
    @patch('backend.pipeline.query.generate_answer_with_gemini')
    def test_rag_query_pipeline_success_full_flow(self, mock_generate_answer, mock_search_chunks, mock_embed_query):
        """Test a successful full RAG pipeline run."""
        mock_embed_query.return_value = [0.1] * 768
        
        mock_chunks = [
            {'content': 'Chunk A content', 'filename': 'A.pdf', 'distance': 0.1, 'rerank_score': 0.9},
            {'content': 'Chunk B content', 'filename': 'B.pdf', 'distance': 0.2, 'rerank_score': 0.8}
        ]
        mock_search_chunks.return_value = mock_chunks
        mock_generate_answer.return_value = "The answer is in the documents."
        
        query_text = "What is A?"
        result = rag_query_pipeline(query_text)

        # Assertions for the final output
        assert result['success'] == True
        assert result['answer'] == "The answer is in the documents."
        assert result['retrieval_count'] == 2
        assert len(result['sources']) == 2
        
        # Verify sources format
        assert result['sources'][0]['filename'] == 'A.pdf'
        assert result['sources'][0]['rerank_score'] == 0.9
        
        # Verify sub-functions were called
        mock_embed_query.assert_called_once_with(query_text)
        mock_search_chunks.assert_called_once()  # Details of call checked implicitly by mock_generate_answer
        mock_generate_answer.assert_called_once_with(query_text, mock_chunks, "gemini-2.5-flash")

        # Verify RAG prompt structure
        assert 'Context:' in result['rag_prompt']
        assert 'Document 1 (A.pdf):' in result['rag_prompt']

    @patch('backend.pipeline.query.genai')
    @patch('os.getenv')
    def test_generate_answer_with_gemini(self, mock_getenv, mock_genai):
        """Test generating answer with Gemini."""
        mock_getenv.return_value = "fake_key"

        # Mock Gemini client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Generated answer"
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        chunks = [{"content": "test content", "filename": "test.txt"}]
        answer = generate_answer_with_gemini("test query", chunks)

        assert answer == "Generated answer"

    @patch('backend.pipeline.query.embed_query')
    def test_rag_query_pipeline_error_handling(self, mock_embed_query):
        """Test query pipeline error handling."""
        mock_embed_query.side_effect = Exception("Test error")

        result = rag_query_pipeline("test query")

        assert result['success'] == False
        assert "Error processing query" in result['answer']
        assert result['sources'] == []
        assert result['retrieval_count'] == 0