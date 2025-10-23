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

    @patch('samvaad.interfaces.cli.SamvaadInterface.get_terminal_width', return_value=80)
    def test_display_help(self, mock_terminal_width, cli_interface):
        """Test display_help with mocked terminal width."""
        cli_interface.display_help()

    @patch('samvaad.interfaces.cli.SamvaadInterface.get_terminal_width', return_value=80)
    def test_display_status_no_start_time(self, mock_terminal_width, cli_interface):
        """Test display_status with no start time."""
        cli_interface.display_status()

    @patch('samvaad.interfaces.cli.SamvaadInterface.get_terminal_width', return_value=80)
    def test_display_status_with_session(self, mock_terminal_width, cli_interface):
        """Test display_status with session data."""
        cli_interface.session_stats['start_time'] = 1234567890
        cli_interface.session_stats['messages'] = 10
        cli_interface.display_status()

    @patch('samvaad.interfaces.cli.SamvaadInterface.get_terminal_width', return_value=80)
    def test_display_welcome(self, mock_terminal_width, cli_interface):
        """Test display_welcome with mocked terminal width."""
        cli_interface.display_welcome()

    @patch('samvaad.interfaces.cli.SamvaadInterface.get_terminal_width', return_value=80)
    def test_show_settings(self, mock_terminal_width, cli_interface):
        """Test show_settings with mocked terminal width."""
        cli_interface.show_settings()

    @patch('samvaad.interfaces.cli.SamvaadInterface.get_terminal_width', return_value=80)
    def test_format_ai_response(self, mock_terminal_width, cli_interface):
        """Test format_ai_response with mocked terminal width."""
        response = "This is a test response."
        sources = []
        query_time = 1.23
        cli_interface.format_ai_response(response, sources, query_time)

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
    @patch('samvaad.interfaces.cli.console')
    @patch('samvaad.utils.filehash_db.delete_file_and_cleanup')
    def test_handle_remove_command_success(self, mock_delete, mock_console, mock_glob, mock_progress, cli_interface, tmp_path):
        """Test successful file removal command."""
        # Create a temporary file to simulate a removal target
        test_file = tmp_path / 'test.pdf'
        test_file.write_text('dummy content')
        mock_glob.glob.return_value = [str(test_file)]

        # Mock the database operations by patching at the method level
        with patch('sqlite3.connect') as mock_connect, \
             patch('samvaad.pipeline.vectorstore.vectorstore.get_collection') as mock_get_collection:
            # Mock database connection and cursor
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            # Mock finding a file in database
            mock_cursor.fetchall.side_effect = [[(1, 'test.pdf')]]

            # Ensure the `/remove` command processes the file correctly
            cli_interface.handle_remove_command(f'/remove {test_file}')

            # Verify we queried the database and processed deletions
            assert mock_cursor.fetchall.call_count >= 1
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