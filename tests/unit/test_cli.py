from unittest.mock import MagicMock, patch

import pytest

# Import the new CLI interface
from samvaad.interfaces.cli import SamvaadInterface


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
        assert "messages" in cli_interface.session_stats
        assert "start_time" in cli_interface.session_stats
        assert "voice_queries" in cli_interface.session_stats
        assert "text_queries" in cli_interface.session_stats
        assert cli_interface.completer is not None
        assert cli_interface.prompt_session is not None

    def test_setup_completions(self, cli_interface):
        """Test completion setup."""
        # Check that completer has expected commands
        completer = cli_interface.completer
        assert hasattr(completer, "commands")
        expected_commands = [
            "/help",
            "/h",
            "/voice",
            "/v",
            "/text",
            "/t",
            "/settings",
            "/cfg",
            "/quit",
            "/q",
            "/exit",
            "/status",
            "/s",
            "/stat",
            "/ingest",
            "/i",
            "/remove",
            "/rm",
        ]
        for cmd in expected_commands:
            assert cmd in completer.commands

    def test_display_banner(self, cli_interface):
        """Test banner display."""
        with patch.object(cli_interface, "console") as mock_console:
            # Mock console.size to avoid comparison issues
            mock_console.size.width = 80
            cli_interface.display_banner()
            # Verify that print was called (banner contains multiple lines)
            assert mock_console.print.call_count > 5

    @patch(
        "samvaad.interfaces.cli.SamvaadInterface.get_terminal_width", return_value=80
    )
    def test_display_help(self, mock_terminal_width, cli_interface):
        """Test display_help with mocked terminal width."""
        cli_interface.display_help()

    @patch(
        "samvaad.interfaces.cli.SamvaadInterface.get_terminal_width", return_value=80
    )
    def test_display_status_no_start_time(self, mock_terminal_width, cli_interface):
        """Test display_status with no start time."""
        cli_interface.display_status()

    @patch(
        "samvaad.interfaces.cli.SamvaadInterface.get_terminal_width", return_value=80
    )
    def test_display_status_with_session(self, mock_terminal_width, cli_interface):
        """Test display_status with session data."""
        cli_interface.session_stats["start_time"] = 1234567890
        cli_interface.session_stats["messages"] = 10
        cli_interface.display_status()

    @patch(
        "samvaad.interfaces.cli.SamvaadInterface.get_terminal_width", return_value=80
    )
    def test_display_welcome(self, mock_terminal_width, cli_interface):
        """Test display_welcome with mocked terminal width."""
        cli_interface.display_welcome()

    @patch(
        "samvaad.interfaces.cli.SamvaadInterface.get_terminal_width", return_value=80
    )
    def test_show_settings(self, mock_terminal_width, cli_interface):
        """Test show_settings with mocked terminal width."""
        cli_interface.show_settings()

    @patch(
        "samvaad.interfaces.cli.SamvaadInterface.get_terminal_width", return_value=80
    )
    def test_format_ai_response(self, mock_terminal_width, cli_interface):
        """Test format_ai_response with mocked terminal width."""
        response = "This is a test response."
        sources = []
        query_time = 1.23
        cli_interface.format_ai_response(response, sources, query_time)

    def test_format_user_message_text(self, cli_interface):
        """Test user message formatting for text mode."""
        with patch.object(cli_interface, "console") as mock_console:
            cli_interface.format_user_message("Hello world", "text")
            assert mock_console.print.called

    def test_format_user_message_voice(self, cli_interface):
        """Test user message formatting for voice mode."""
        with patch.object(cli_interface, "console") as mock_console:
            message = "Hello world"
            cli_interface.format_user_message(message, "voice")
            assert mock_console.print.called

    def test_handle_slash_command_help(self, cli_interface):
        """Test help command handling."""
        with patch.object(cli_interface, "display_help") as mock_display:
            result = cli_interface.handle_slash_command("/help")
            assert result is True
            mock_display.assert_called_once()

    def test_handle_slash_command_status(self, cli_interface):
        """Test status command handling."""
        with patch.object(cli_interface, "display_status") as mock_display:
            result = cli_interface.handle_slash_command("/status")
            assert result is True
            mock_display.assert_called_once()

    def test_handle_slash_command_quit(self, cli_interface):
        """Test quit command handling."""
        result = cli_interface.handle_slash_command("/quit")
        assert result is False  # Should return False to exit

    def test_handle_slash_command_unknown(self, cli_interface):
        """Test unknown command handling."""
        with patch.object(cli_interface.console, "print") as mock_print:
            result = cli_interface.handle_slash_command("/unknown")
            assert result is True
            mock_print.assert_called()

    @patch("samvaad.interfaces.cli.Progress")
    @patch("samvaad.interfaces.cli.glob")
    @patch("samvaad.interfaces.cli.console")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("mimetypes.guess_type")
    def test_handle_ingest_command_success(
        self,
        mock_mimetype,
        mock_open,
        mock_console,
        mock_glob,
        mock_progress,
        cli_interface,
        tmp_path,
    ):
        """Test successful file ingestion command."""
        # Create a real temporary file
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"PDF content")

        # Mock file discovery to return our temp file
        mock_glob.glob.return_value = [str(test_file)]

        # Mock mimetype detection
        mock_mimetype.return_value = ("application/pdf", None)

        # Mock the ingestion pipeline after it gets imported
        with patch(
            "samvaad.pipeline.ingestion.ingestion.ingest_file_pipeline_with_progress"
        ) as mock_ingest:
            mock_ingest.return_value = {
                "num_chunks": 10,
                "new_chunks_embedded": 8,
                "error": None,
            }

            # This should succeed without errors
            cli_interface.handle_ingest_command(f"/ingest {test_file}")

            # Verify ingestion was called
            assert mock_ingest.call_count == 1

    @patch("samvaad.interfaces.cli.Progress")


    @patch("samvaad.pipeline.retrieval.query.rag_query_pipeline")
    @patch("samvaad.interfaces.cli.Progress")
    @patch("samvaad.interfaces.cli.time")
    @patch("samvaad.interfaces.cli.console")
    def test_process_text_query_success(
        self, mock_console, mock_time, mock_progress, mock_rag, cli_interface
    ):
        """Test successful text query processing."""
        # Mock time
        mock_time.time.side_effect = [100.0, 101.5]  # Start and end times

        # Mock successful RAG response
        mock_rag.return_value = {
            "answer": "Test answer",
            "success": True,
            "sources": [{"filename": "test.txt"}],
        }

        result = cli_interface.process_text_query("test query")

        # Verify RAG pipeline was called with correct arguments
        mock_rag.assert_called_once()
        call_kwargs = mock_rag.call_args
        assert call_kwargs[0][0] == "test query"  # First positional arg

        # Verify result structure
        assert result["answer"] == "Test answer"
        assert result["success"] is True
        assert "query_time" in result
        assert result["query_time"] == 1.5

        # Verify stats were updated
        assert cli_interface.session_stats["messages"] == 1
        assert cli_interface.session_stats["text_queries"] == 1

    @patch("samvaad.pipeline.retrieval.query.rag_query_pipeline")
    @patch("samvaad.interfaces.cli.Progress")
    @patch("samvaad.interfaces.cli.time")
    @patch("samvaad.interfaces.cli.console")
    def test_process_text_query_error(
        self, mock_console, mock_time, mock_progress, mock_rag, cli_interface
    ):
        """Test text query processing with error."""
        # Mock time
        mock_time.time.side_effect = [100.0, 101.0]

        # Mock RAG pipeline error
        mock_rag.side_effect = Exception("API Error")

        result = cli_interface.process_text_query("test query")

        # Verify error handling
        assert "error" in result["answer"].lower()
        assert result["success"] is False
        assert "query_time" in result

    @patch("samvaad.interfaces.cli.console")
    def test_show_thinking_indicator(self, mock_console, cli_interface):
        """Test thinking indicator display."""
        cli_interface.show_thinking_indicator("Processing...")
        # This uses console.status which is harder to mock directly
        # Just verify the method exists and can be called
        assert True

    @patch("samvaad.pipeline.retrieval.query.rag_query_pipeline")
    @patch("samvaad.interfaces.cli.Progress")
    def test_process_text_query_success(self, mock_progress, mock_rag, cli_interface):
        """Test processing text query successfully."""
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = "task_id"

        mock_rag.return_value = {
            "answer": "Test response",
            "success": True,
            "sources": [],
        }

        result = cli_interface.process_text_query("Test query")

        assert result["answer"] == "Test response"
        assert result["success"] is True
        assert "query_time" in result

    @patch("samvaad.pipeline.retrieval.query.rag_query_pipeline")
    @patch("samvaad.interfaces.cli.Progress")
    def test_process_text_query_error(self, mock_progress, mock_rag, cli_interface):
        """Test processing text query with error."""
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = "task_id"

        mock_rag.side_effect = Exception("Query error")

        result = cli_interface.process_text_query("Test query")

        assert "error" in result["answer"]
        assert result["success"] is False
