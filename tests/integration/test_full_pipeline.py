import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
import shutil

# Import pipeline functions
from backend.pipeline.ingestion.preprocessing import preprocess_file
from backend.pipeline.ingestion.chunking import parse_file, chunk_text, find_new_chunks, update_chunk_file_db
from backend.pipeline.ingestion.embedding import embed_chunks_with_dedup
from backend.pipeline.vectorstore.vectorstore import add_embeddings
from backend.pipeline.deletion.deletion import delete_file_and_embeddings
from backend.pipeline.retrieval.query import rag_query_pipeline


class TestFullPipeline:
    """Integration tests for the complete RAG pipeline."""

    def setup_method(self):
        """Set up temporary directories and databases for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_filehashes.sqlite3')
        self.chroma_path = os.path.join(self.temp_dir, 'test_chroma')

    def teardown_method(self):
        """Clean up temporary directories."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('backend.utils.filehash_db.DB_PATH')
    @patch('backend.pipeline.ingestion.chunking.chunk_exists')
    @patch('backend.pipeline.ingestion.embedding.collection')
    @patch('backend.pipeline.vectorstore.vectorstore.collection')
    @patch('backend.pipeline.deletion.deletion.open', new_callable=lambda: MagicMock())
    @patch('backend.pipeline.deletion.deletion.generate_file_id')
    @patch('backend.pipeline.deletion.deletion.delete_file_and_cleanup')
    def test_full_pipeline_ingest_query_delete(self, mock_cleanup, mock_gen_id, mock_file_open,
                                               mock_vs_collection, mock_emb_collection,
                                               mock_chunk_exists, mock_db_path):
        """Test the full pipeline: ingest -> query -> delete."""

        # Setup mocks
        mock_db_path.__str__ = lambda: self.db_path
        mock_db_path.new = self.db_path

        # Mock chunk doesn't exist
        mock_chunk_exists.return_value = False

        # Mock collections
        mock_emb_collection.get.return_value = {"ids": []}  # No existing embeddings
        mock_vs_collection.get.return_value = {"ids": []}  # No existing in vectorstore

        # Mock file content for deletion
        mock_file_handle = MagicMock()
        mock_file_handle.__enter__.return_value = mock_file_handle
        mock_file_handle.read.return_value = b"test content"
        mock_file_open.return_value = mock_file_handle
        mock_gen_id.return_value = "test_file_id"
        mock_cleanup.return_value = ["chunk1"]

        # Test data
        test_content = b"This is a test document for integration testing."
        test_filename = "test.txt"
        test_query = "What is this document about?"

        # Step 1: Preprocessing
        with patch('backend.pipeline.ingestion.preprocessing.init_db'), \
             patch('backend.pipeline.ingestion.preprocessing.file_exists', return_value=False):

            is_duplicate = preprocess_file(test_content, test_filename)
            assert not is_duplicate

        # Step 2: Parsing
        with patch('backend.pipeline.ingestion.chunking.get_docling_converter'), \
             patch('backend.pipeline.ingestion.chunking.tempfile.NamedTemporaryFile') as mock_temp, \
             patch('backend.pipeline.ingestion.chunking.os.unlink'):

            # Mock temp file
            mock_temp_file = MagicMock()
            mock_temp_file.__enter__.return_value = mock_temp_file
            mock_temp_file.__exit__.return_value = None
            mock_temp_file.name = "/tmp/test.txt"
            mock_temp.return_value = mock_temp_file

            text, error = parse_file(test_filename, "text/plain", test_content)
            assert text == "This is a test document for integration testing."
            assert error is None

        # Step 3: Chunking
        chunks = chunk_text(text)
        assert isinstance(chunks, list)
        assert len(chunks) > 0

        # Step 4: Find new chunks
        new_chunks = find_new_chunks(chunks, "test_file_id")
        assert len(new_chunks) > 0

        # Step 5: Update chunk database
        with patch('backend.pipeline.ingestion.chunking.add_chunk'):
            update_chunk_file_db(chunks, "test_file_id")

        # Step 6: Embedding (mock the model)
        with patch('backend.pipeline.ingestion.embedding._model', MagicMock()) as mock_model, \
             patch('backend.pipeline.ingestion.embedding.get_device', return_value='cpu'):

            # Mock numpy array with tolist() method
            mock_embeddings = MagicMock()
            mock_embeddings.tolist.return_value = [[0.1] * 768 for _ in range(len(chunks))]
            mock_model.encode.return_value = mock_embeddings

            embeddings, indices = embed_chunks_with_dedup(chunks, test_filename)
            assert len(embeddings) == len(chunks)
            assert len(indices) == len(chunks)

        # Step 7: Add to vectorstore
        metadatas = [{"filename": test_filename, "chunk_id": f"chunk_{i}"} for i in range(len(chunks))]
        add_embeddings(chunks, embeddings, metadatas, test_filename)

        # Step 8: Query pipeline (mock external dependencies)
        with patch('backend.pipeline.retrieval.query.get_embedding_model') as mock_emb_model, \
             patch('backend.pipeline.retrieval.query.search_similar_chunks') as mock_search, \
             patch('backend.pipeline.retrieval.query.generate_answer_with_gemini') as mock_generate:

            mock_emb_model_instance = MagicMock()
            mock_embedding = MagicMock()
            mock_embedding.tolist.return_value = [[0.1] * 768]
            mock_emb_model_instance.encode.return_value = mock_embedding
            mock_emb_model.return_value = mock_emb_model_instance

            mock_search.return_value = [{
                'content': 'test chunk',
                'filename': test_filename,
                'distance': 0.1,
                'rerank_score': 0.9
            }]

            mock_generate.return_value = "This document is about integration testing."

            result = rag_query_pipeline(test_query)

            assert result['success'] == True
            assert 'integration testing' in result['answer']
            assert len(result['sources']) > 0

        # Step 9: Delete file and embeddings
        orphaned = delete_file_and_embeddings(test_filename)
        assert isinstance(orphaned, list)

        # Verify cleanup was called
        mock_cleanup.assert_called_once_with("test_file_id")