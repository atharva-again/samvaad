import pytest
from unittest.mock import patch, MagicMock, call
import tempfile
import os
import sys
import sqlite3
from pathlib import Path

# Import the new CLI interface
from samvaad.interfaces.cli import SamvaadInterface, Colors


class TestSamvaadInterface:
    """Test cases for the new SamvaadInterface CLI."""

    @pytest.fixture
    def cli_interface(self):
        """Create a CLI interface instance for testing."""
        return SamvaadInterface()

    def test_initialization(self, cli_interface):
        """Test CLI interface initialization."""
        assert cli_interface.console is not None
        assert cli_interface.conversation_active is False
        assert cli_interface._should_exit is False
        assert 'messages' in cli_interface.session_stats
        assert 'start_time' in cli_interface.session_stats
        assert 'voice_queries' in cli_interface.session_stats
        assert 'text_queries' in cli_interface.session_stats
        assert cli_interface.completer is not None
        assert cli_interface.prompt_session is not None

    def test_setup_completions(self, cli_interface):
        """Test completion setup."""
        # Check that completer has expected commands
        completer = cli_interface.completer
        assert hasattr(completer, 'commands')
        expected_commands = ['/help', '/h', '/voice', '/v', '/text', '/t',
                           '/settings', '/cfg', '/quit', '/q', '/exit',
                           '/status', '/s', '/stat', '/ingest', '/i',
                           '/remove', '/rm']
        for cmd in expected_commands:
            assert cmd in completer.commands

    def test_display_banner(self, cli_interface):
        """Test banner display."""
        with patch.object(cli_interface, 'console') as mock_console:
            # Mock console.size to avoid comparison issues
            mock_console.size.width = 80
            cli_interface.display_banner()
            # Verify that print was called (banner contains multiple lines)
            assert mock_console.print.call_count > 5

    def test_display_help(self, cli_interface):
        """Test help display."""
        with patch.object(cli_interface, 'console') as mock_console:
            cli_interface.display_help()
            # Verify help panel was created and printed
            assert mock_console.print.called
            call_args = mock_console.print.call_args
            assert 'Panel' in str(call_args)

    def test_display_status_no_start_time(self, cli_interface):
        """Test status display when no session started."""
        with patch.object(cli_interface, 'console') as mock_console:
            cli_interface.display_status()
            # Should show appropriate message for no start time
            assert mock_console.print.called

    def test_display_status_with_session(self, cli_interface):
        """Test status display with active session."""
        with patch.object(cli_interface, 'console') as mock_console, \
             patch('samvaad.interfaces.cli.time') as mock_time:
            # Set up session stats
            cli_interface.session_stats['start_time'] = 1000
            cli_interface.session_stats['messages'] = 5
            cli_interface.session_stats['voice_queries'] = 2
            cli_interface.session_stats['text_queries'] = 3

            mock_time.time.return_value = 1100  # 100 seconds later

            cli_interface.display_status()

            # Verify table was printed
            assert mock_console.print.called

    def test_display_welcome(self, cli_interface):
        """Test welcome message display."""
        with patch.object(cli_interface, 'console') as mock_console:
            cli_interface.display_welcome()
            assert mock_console.print.called

    def test_show_settings(self, cli_interface):
        """Test settings display."""
        with patch.object(cli_interface, 'console') as mock_console:
            cli_interface.show_settings()
            assert mock_console.print.called

    def test_format_ai_response(self, cli_interface):
        """Test AI response formatting."""
        with patch.object(cli_interface, 'console') as mock_console:
            response = "Test response"
            sources = [{"filename": "test.txt", "content_preview": "content"}]
            query_time = 1.5

            cli_interface.format_ai_response(response, sources, query_time)

            # Verify response panel was created
            assert mock_console.print.called

    def test_format_user_message_text(self, cli_interface):
        """Test user message formatting for text mode."""
        with patch.object(cli_interface, 'console') as mock_console:
            cli_interface.format_user_message("Hello world", "text")
            assert mock_console.print.called

    def test_format_user_message_voice(self, cli_interface):
        """Test user message formatting for voice mode."""
        with patch.object(cli_interface, 'console') as mock_console:
            message = "Hello world"
            cli_interface.format_user_message(message, "voice")
            assert mock_console.print.called

    def test_handle_slash_command_help(self, cli_interface):
        """Test help command handling."""
        with patch.object(cli_interface, 'display_help') as mock_display:
            result = cli_interface.handle_slash_command('/help')
            assert result is True
            mock_display.assert_called_once()

    def test_handle_slash_command_status(self, cli_interface):
        """Test status command handling."""
        with patch.object(cli_interface, 'display_status') as mock_display:
            result = cli_interface.handle_slash_command('/status')
            assert result is True
            mock_display.assert_called_once()

    def test_handle_slash_command_quit(self, cli_interface):
        """Test quit command handling."""
        result = cli_interface.handle_slash_command('/quit')
        assert result is False  # Should return False to exit

    def test_handle_slash_command_unknown(self, cli_interface):
        """Test unknown command handling."""
        with patch.object(cli_interface.console, 'print') as mock_print:
            result = cli_interface.handle_slash_command('/unknown')
            assert result is True
            mock_print.assert_called()

    @patch('samvaad.interfaces.cli.Progress')
    @patch('samvaad.pipeline.ingestion.ingestion.ingest_file_pipeline')
    @patch('samvaad.interfaces.cli.glob')
    @patch('samvaad.interfaces.cli.os')
    @patch('samvaad.interfaces.cli.console')
    def test_handle_ingest_command_success(self, mock_console, mock_os, mock_glob, mock_ingest, mock_progress, cli_interface):
        """Test successful file ingestion command."""
        # Mock file discovery
        mock_glob.glob.return_value = ['test.pdf']
        mock_os.path.isfile.return_value = True
        mock_os.path.getsize.return_value = 1000

        # Mock successful ingestion
        mock_ingest.return_value = {
            'num_chunks': 10,
            'new_chunks_embedded': 8,
            'error': None
        }

        # Mock file reading
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b'file content'
            mock_open.return_value.__enter__.return_value = mock_file

            cli_interface.handle_ingest_command('/ingest test.pdf')

            # Verify ingestion was called
            mock_ingest.assert_called_once()

    @patch('samvaad.interfaces.cli.Progress')
    @patch('samvaad.interfaces.cli.glob')
    @patch('samvaad.interfaces.cli.os')
    @patch('samvaad.interfaces.cli.console')
    @patch('samvaad.utils.filehash_db.delete_file_and_cleanup')
    def test_handle_remove_command_success(self, mock_delete, mock_console, mock_os, mock_glob, mock_progress, cli_interface):
        """Test successful file removal command."""
        # Mock file discovery - glob should return a unique list (set-like behavior)
        mock_glob.glob.return_value = ['test.pdf']
        mock_os.path.isfile.return_value = True

        # Mock the database operations by patching at the method level
        with patch('samvaad.interfaces.cli.sqlite3') as mock_sqlite, \
             patch('samvaad.pipeline.vectorstore.vectorstore.get_collection') as mock_get_collection:
            # Mock database connection and cursor
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_sqlite.connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            # Mock finding a file in database
            mock_cursor.fetchall.return_value = [(1, 'test.pdf')]

            # Mock successful deletion
            mock_delete.return_value = [1, 2, 3, 4, 5]  # 5 orphaned chunks

            # Mock collection for ChromaDB deletion
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection

            cli_interface.handle_remove_command('/remove test.pdf')

            # Verify deletion was called at least once
            assert mock_delete.call_count >= 1

    @patch('samvaad.pipeline.retrieval.query.rag_query_pipeline')
    @patch('samvaad.interfaces.cli.Progress')
    @patch('samvaad.interfaces.cli.time')
    @patch('samvaad.interfaces.cli.console')
    def test_process_text_query_success(self, mock_console, mock_time, mock_progress, mock_rag, cli_interface):
        """Test successful text query processing."""
        # Mock time
        mock_time.time.side_effect = [100.0, 101.5]  # Start and end times

        # Mock successful RAG response
        mock_rag.return_value = {
            'answer': 'Test answer',
            'success': True,
            'sources': [{'filename': 'test.txt'}]
        }

        result = cli_interface.process_text_query('test query')

        # Verify RAG pipeline was called
        mock_rag.assert_called_once_with(
            'test query',
            model='gemini-2.5-flash',
            conversation_manager=cli_interface.conversation_manager
        )

        # Verify result structure
        assert result['answer'] == 'Test answer'
        assert result['success'] is True
        assert 'query_time' in result
        assert result['query_time'] == 1.5

        # Verify stats were updated
        assert cli_interface.session_stats['messages'] == 1
        assert cli_interface.session_stats['text_queries'] == 1

    @patch('samvaad.pipeline.retrieval.query.rag_query_pipeline')
    @patch('samvaad.interfaces.cli.Progress')
    @patch('samvaad.interfaces.cli.time')
    @patch('samvaad.interfaces.cli.console')
    def test_process_text_query_error(self, mock_console, mock_time, mock_progress, mock_rag, cli_interface):
        """Test text query processing with error."""
        # Mock time
        mock_time.time.side_effect = [100.0, 101.0]

        # Mock RAG pipeline error
        mock_rag.side_effect = Exception('API Error')

        result = cli_interface.process_text_query('test query')

        # Verify error handling
        assert 'error' in result['answer'].lower()
        assert result['success'] is False
        assert 'query_time' in result

    @patch('samvaad.interfaces.cli.console')
    def test_show_thinking_indicator(self, mock_console, cli_interface):
        """Test thinking indicator display."""
        cli_interface.show_thinking_indicator("Processing...")
        # This uses console.status which is harder to mock directly
        # Just verify the method exists and can be called
        assert True

    @patch('samvaad.pipeline.retrieval.voice_mode.VoiceMode')
    @patch('samvaad.pipeline.retrieval.voice_mode.initialize_whisper_model')
    @patch('samvaad.pipeline.retrieval.query.get_embedding_model')
    @patch('samvaad.pipeline.retrieval.voice_mode.get_kokoro_tts')
    @patch('samvaad.pipeline.retrieval.voice_mode.ConversationManager')
    @patch('samvaad.interfaces.cli.Progress')
    @patch('samvaad.interfaces.cli.console')
    def test_start_voice_mode_success(self, mock_console, mock_progress, mock_conv_manager, mock_tts, mock_embedding, mock_whisper, mock_voice_mode):
        """Test starting voice mode successfully."""
        cli_interface = SamvaadInterface()
        cli_interface.console = mock_console

        # Mock the progress context manager
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = "task_id"

        # Mock voice mode
        mock_voice_instance = MagicMock()
        mock_voice_mode.return_value = mock_voice_instance

        cli_interface.start_voice_mode()

        # Verify progress was used
        mock_progress.assert_called()
        # Verify models were initialized
        mock_whisper.assert_called_once()
        mock_embedding.assert_called_once()
        mock_tts.assert_called_once()
        # Verify voice mode was created and run
        mock_voice_mode.assert_called_once()
        mock_voice_instance.run.assert_called_once()

    @patch('samvaad.pipeline.retrieval.voice_mode.VoiceMode')
    @patch('samvaad.interfaces.cli.Progress')
    @patch('samvaad.interfaces.cli.console')
    def test_run_voice_conversation_success(self, mock_console, mock_progress, mock_voice_mode):
        """Test running voice conversation successfully."""
        cli_interface = SamvaadInterface()
        cli_interface.console = mock_console

        # Mock voice mode
        mock_voice_instance = MagicMock()
        mock_voice_mode.return_value = mock_voice_instance

        cli_interface.run_voice_conversation()

        # Verify voice mode was created and run
        mock_voice_mode.assert_called_once()
        mock_voice_instance.run.assert_called_once()

    @patch('samvaad.pipeline.retrieval.voice_mode.VoiceMode')
    @patch('samvaad.interfaces.cli.Progress')
    @patch('samvaad.interfaces.cli.console')
    def test_run_voice_conversation_error(self, mock_console, mock_progress, mock_voice_mode):
        """Test running voice conversation with error."""
        cli_interface = SamvaadInterface()
        cli_interface.console = mock_console

        # Mock voice mode to raise exception
        mock_voice_mode.side_effect = Exception("Voice error")

        cli_interface.run_voice_conversation()

        # Verify error message was printed
        mock_console.print.assert_called()

    @patch('samvaad.pipeline.retrieval.voice_mode.ConversationManager')
    def test_init_conversation_components_success(self, mock_conv_manager, cli_interface):
        """Test initializing conversation components successfully."""
        mock_manager_instance = MagicMock()
        mock_conv_manager.return_value = mock_manager_instance

        cli_interface.init_conversation_components()

        # Verify conversation manager was created
        mock_conv_manager.assert_called_once_with(max_history=50, context_window=10)
        assert cli_interface.conversation_manager == mock_manager_instance

    @patch('samvaad.pipeline.retrieval.voice_mode.ConversationManager')
    def test_init_conversation_components_error(self, mock_conv_manager, cli_interface):
        """Test initializing conversation components with error."""
        mock_conv_manager.side_effect = Exception("Init error")

        with patch.object(cli_interface, 'console') as mock_console:
            cli_interface.init_conversation_components()

            # Verify error message was printed
            mock_console.print.assert_called()

    @patch('samvaad.pipeline.retrieval.query.rag_query_pipeline')
    @patch('samvaad.interfaces.cli.Progress')
    def test_process_text_query_success(self, mock_progress, mock_rag, cli_interface):
        """Test processing text query successfully."""
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = "task_id"

        mock_rag.return_value = {
            'answer': 'Test response',
            'success': True,
            'sources': []
        }

        result = cli_interface.process_text_query("Test query")

        assert result['answer'] == 'Test response'
        assert result['success'] is True
        assert 'query_time' in result

    @patch('samvaad.pipeline.retrieval.query.rag_query_pipeline')
    @patch('samvaad.interfaces.cli.Progress')
    def test_process_text_query_error(self, mock_progress, mock_rag, cli_interface):
        """Test processing text query with error."""
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = "task_id"

        mock_rag.side_effect = Exception("Query error")

        result = cli_interface.process_text_query("Test query")

        assert "error" in result['answer']
        assert result['success'] is False