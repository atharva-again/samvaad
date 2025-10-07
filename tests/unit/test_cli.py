import pytest
from unittest.mock import patch, MagicMock
import tempfile
import os
import sys
import importlib.util
from pathlib import Path

# Import CLI functions to test - avoid 'test' module name conflict
backend_test_path = os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'test.py')
spec = importlib.util.spec_from_file_location("backend_test", backend_test_path)
backend_test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend_test)
# Expose the dynamically loaded module so patch() lookups succeed.
sys.modules.setdefault("backend_test", backend_test)

# Import CLI functions to test
strip_markdown = backend_test.strip_markdown
resolve_document_path = backend_test.resolve_document_path
print_help = backend_test.print_help
handle_query_interactive = backend_test.handle_query_interactive
remove_file_interactive = backend_test.remove_file_interactive
process_file_interactive = backend_test.process_file_interactive
test_path_resolution = backend_test.test_path_resolution


class TestCLIUtils:
    """Test CLI utility functions."""

    def test_resolve_document_path_absolute(self):
        """Test resolving absolute paths."""
        abs_path = "/absolute/path/to/file.pdf"
        result = resolve_document_path(abs_path)
        assert result == abs_path

    def test_resolve_document_path_relative(self):
        """Test resolving relative paths to documents directory."""
        # Mock the path operations
        with patch('os.path.dirname', return_value='/fake/samvaad'), \
             patch('os.path.join') as mock_join, \
             patch('os.path.isabs', return_value=False):

            def join_side_effect(*args):
                # Simulate os.path.join behaviour for both base path and final path computation.
                if args == ('/fake/samvaad', 'data', 'documents'):
                    return '/fake/samvaad/data/documents'
                return '/'.join(args)

            mock_join.side_effect = join_side_effect

            result = resolve_document_path("test.pdf")
            assert result == '/fake/samvaad/data/documents/test.pdf'
            mock_join.assert_any_call('/fake/samvaad/data/documents', 'test.pdf')

    def test_resolve_document_path_already_in_documents(self):
        """Test paths already in documents directory."""
        doc_path = "/fake/samvaad/data/documents/file.pdf"
        with patch('backend_test.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = "/fake/samvaad"

            result = resolve_document_path(doc_path)
            assert result == doc_path

    @patch('builtins.print')
    def test_print_help(self, mock_print):
        """Test help message printing."""
        print_help()

        # Verify that help was printed (check that print was called multiple times)
        assert mock_print.call_count > 5

        # Check some key help content
        calls = [str(call) for call in mock_print.call_args_list]
        help_text = ' '.join(calls)

        assert 'Available commands:' in help_text
        assert '/query' in help_text
        assert '/voice' in help_text
        assert '/ingest' in help_text
        assert '/remove' in help_text

    @patch('backend.pipeline.retrieval.query.rag_query_pipeline')
    @patch('time.perf_counter')
    @patch('builtins.print')
    def test_handle_query_interactive(self, mock_print, mock_perfcounter, mock_rag):
        """Test interactive query handling."""
        mock_perfcounter.side_effect = [100.0, 105.5]  # Start and end times

        mock_rag.return_value = {
            "success": True,
            "answer": "Test answer",
            "sources": [{"filename": "test.txt", "content_preview": "content", "distance": 0.1}],
            "query": "test query",
            "retrieval_count": 1,
            "rag_prompt": "test prompt"
        }

        handle_query_interactive("test query")

        # Verify RAG pipeline was called
        mock_rag.assert_called_once_with("test query", top_k=3, model="gemini-2.5-flash")

        # Verify output was printed
        assert mock_print.call_count > 5

    @patch('backend.pipeline.deletion.deletion.delete_file_and_embeddings')
    @patch('time.perf_counter')
    @patch('builtins.print')
    def test_remove_file_interactive(self, mock_print, mock_perfcounter, mock_delete):
        """Test interactive file removal."""
        mock_perfcounter.side_effect = [200.0, 202.5]
        mock_delete.return_value = [1, 2, 3]  # Orphaned chunk IDs

        with patch('backend_test.resolve_document_path', return_value="/path/to/file.pdf"):
            remove_file_interactive("file.pdf")

            mock_delete.assert_called_once_with("/path/to/file.pdf")
            assert mock_print.call_count > 2

    @patch('backend.pipeline.ingestion.ingestion.ingest_file_pipeline')
    @patch('time.perf_counter')
    @patch('builtins.print')
    @patch('builtins.open', create=True)
    def test_process_file_interactive(self, mock_open, mock_print, mock_perfcounter, mock_ingest):
        """Test interactive file processing."""
        mock_perfcounter.side_effect = [300.0, 305.0]

        mock_ingest.return_value = {
            "num_chunks": 10,
            "new_chunks_embedded": 8,
            "error": None,
            "chunk_preview": ["chunk1", "chunk2", "chunk3"]
        }

        # Mock file operations
        mock_file = MagicMock()
        mock_file.read.return_value = b"file content"
        mock_open.return_value.__enter__.return_value = mock_file

        with patch('backend_test.resolve_document_path', return_value="/path/to/file.pdf"), \
             patch('os.path.isfile', return_value=True), \
             patch('os.path.splitext', return_value=("/path/to/file", ".pdf")):

            process_file_interactive("file.pdf")

            mock_ingest.assert_called_once()
            args, kwargs = mock_ingest.call_args
            assert args[0] == "/path/to/file.pdf"
            assert args[1] == "application/pdf"
            assert args[2] == b"file content"

    @patch('os.path.isfile', return_value=False)
    @patch('builtins.print')
    def test_process_file_interactive_file_not_found(self, mock_print, mock_isfile):
        """Test file processing when file doesn't exist."""
        with patch('backend_test.resolve_document_path', return_value="/nonexistent/file.pdf"):
            process_file_interactive("file.pdf")

            mock_print.assert_called_with("File not found: /nonexistent/file.pdf")

    @patch('builtins.print')
    def test_test_path_resolution(self, mock_print):
        """Test path resolution testing function."""
        with patch('os.path.dirname', return_value="/fake/samvaad"), \
             patch('os.path.join') as mock_join:

            mock_join.side_effect = lambda *args: "/".join(args)

            test_path_resolution()

            # Verify print was called for test results
            assert mock_print.call_count > 3

    @patch('backend.test.interactive_cli')
    @patch('backend.test.test_path_resolution')
    @patch('sys.argv', ['test.py', '--test-paths'])
    def test_main_with_test_paths(self, mock_test_paths, mock_interactive_cli):
        """Test main function with --test-paths flag."""
        from backend.test import main

        main()

        mock_test_paths.assert_called_once()
        mock_interactive_cli.assert_not_called()

    @patch('backend.test.interactive_cli')
    @patch('sys.argv', ['test.py'])
    def test_main_default(self, mock_interactive_cli):
        """Test main function default behavior."""
        from backend.test import main

        main()

        mock_interactive_cli.assert_called_once()