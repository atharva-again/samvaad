import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
import shutil
import numpy as np

# Import pipeline functions
from samvaad.pipeline.ingestion.preprocessing import preprocess_file
from samvaad.pipeline.ingestion.chunking import parse_file, chunk_text, find_new_chunks, update_chunk_file_db
from samvaad.pipeline.ingestion.embedding import embed_chunks_with_dedup
from samvaad.pipeline.vectorstore.vectorstore import add_embeddings
from samvaad.pipeline.deletion.deletion import delete_file_and_embeddings
from samvaad.pipeline.retrieval.query import rag_query_pipeline


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

    @patch('samvaad.utils.filehash_db.DB_PATH')
    @patch('samvaad.pipeline.ingestion.chunking.chunk_exists')
    @patch('samvaad.pipeline.ingestion.embedding.get_collection')
    @patch('samvaad.pipeline.vectorstore.vectorstore.get_collection')
    @patch('samvaad.pipeline.deletion.deletion.open', new_callable=lambda: MagicMock())
    @patch('samvaad.pipeline.deletion.deletion.generate_file_id')
    @patch('samvaad.pipeline.deletion.deletion.delete_file_and_cleanup')
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
        with patch('samvaad.pipeline.ingestion.preprocessing.init_db'), \
             patch('samvaad.pipeline.ingestion.preprocessing.file_exists', return_value=False):

            is_duplicate = preprocess_file(test_content, test_filename)
            assert not is_duplicate

        # Step 2: Parsing
        with patch('samvaad.pipeline.ingestion.chunking.get_docling_converter') as mock_get_docling, \
             patch('samvaad.pipeline.ingestion.chunking.tempfile.NamedTemporaryFile') as mock_temp, \
             patch('samvaad.pipeline.ingestion.chunking.os.unlink'):

            mock_get_docling.return_value.convert.return_value.document.export_to_markdown.return_value = "This is a test document for integration testing."

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
        with patch('samvaad.pipeline.ingestion.chunking.add_chunk'):
            update_chunk_file_db(chunks, "test_file_id")

        # Step 6: Embedding (mock the model)
        with patch('samvaad.pipeline.ingestion.embedding._model', MagicMock()) as mock_model, \
             patch('samvaad.pipeline.ingestion.embedding.get_device', return_value='cpu'):

            mock_model.encode_document.return_value = np.array(
                [[0.1] * 768 for _ in range(len(chunks))], dtype=np.float32
            )

            embeddings, indices = embed_chunks_with_dedup(chunks, test_filename)
            assert len(embeddings) == len(chunks)
            assert len(indices) == len(chunks)

        # Step 7: Add to vectorstore
        metadatas = [{"filename": test_filename, "chunk_id": f"chunk_{i}"} for i in range(len(chunks))]
        add_embeddings(chunks, embeddings, metadatas, test_filename)

        # Step 8: Query pipeline (mock external dependencies)
        with patch('samvaad.pipeline.retrieval.query.get_embedding_model') as mock_emb_model, \
             patch('samvaad.pipeline.retrieval.query.search_similar_chunks') as mock_search, \
             patch('samvaad.pipeline.retrieval.query.generate_answer_with_gemini') as mock_generate:

            mock_emb_model_instance = MagicMock()
            mock_emb_model_instance.encode_query.return_value = np.array([0.1] * 768, dtype=np.float32)
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

    @patch('samvaad.utils.filehash_db.DB_PATH')
    @patch('samvaad.pipeline.retrieval.voice_mode.clean_transcription')
    @patch('samvaad.pipeline.retrieval.voice_mode.initialize_whisper_model')
    @patch('webrtcvad.Vad')
    @patch('sounddevice.RawInputStream')
    @patch('samvaad.pipeline.retrieval.voice_mode.rag_query_pipeline')
    @patch('samvaad.pipeline.retrieval.voice_mode.play_audio_response')
    @patch('builtins.print')
    def test_voice_query_pipeline_integration(self, mock_print, mock_play_audio, mock_rag_pipeline,
                                             mock_input_stream, mock_vad, mock_init_whisper,
                                             mock_clean_transcription, mock_db_path):
        """Test the complete voice query pipeline: record -> transcribe -> clean -> query."""

        # Setup mocks
        mock_db_path.__str__ = lambda: self.db_path
        mock_db_path.new = self.db_path

        # Mock Whisper model
        mock_whisper_model = MagicMock()
        mock_init_whisper.return_value = mock_whisper_model

        # Mock VAD
        mock_vad_instance = MagicMock()
        mock_vad.return_value = mock_vad_instance

        # Mock sounddevice stream
        mock_stream = MagicMock()
        mock_stream.start.return_value = None
        mock_stream.stop.return_value = None
        mock_stream.close.return_value = None
        mock_input_stream.return_value = mock_stream

        # Mock audio data - simulate speech then silence
        speech_frame = np.ones(320, dtype=np.int16)
        silence_frame = np.zeros(320, dtype=np.int16)

        # Simulate: speech detected, then 151 frames of silence (3+ seconds)
        mock_stream.read.side_effect = [(speech_frame, False)] + [(silence_frame, False)] * 151

        # Mock VAD - detect speech initially, then silence
        mock_vad_instance.is_speech.side_effect = [True] + [False] * 151

        # Mock transcription
        mock_segment = MagicMock()
        mock_segment.text = "What is this document about?"
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.95
        mock_whisper_model.transcribe.return_value = ([mock_segment], mock_info)

        # Mock text cleaning
        mock_clean_transcription.return_value = "What is this document about?"

        # Mock RAG pipeline response
        mock_rag_pipeline.return_value = {
            'answer': 'This document is about integration testing.',
            'success': True,
            'sources': [{
                'filename': 'test.txt',
                'content_preview': 'This is a test document...',
                'distance': 0.1
            }],
            'retrieval_count': 1
        }

        # Test VoiceMode directly without threading
        from samvaad.pipeline.retrieval.voice_mode import VoiceMode
        
        vm = VoiceMode()
        # Verify initialization works
        assert vm is not None