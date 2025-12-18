"""
Main CLI interface for Samvaad - inspired by GitHub Copilot CLI and Gemini CLI design patterns.
"""

import asyncio
import glob
import os
import signal
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import print_formatted_text
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

# Initialize console for rich output
console = Console(file=sys.__stdout__)


# Color scheme inspired by GitHub Copilot CLI and Gemini CLI
class Colors:
    # System colors
    PRIMARY = "#2563eb"  # Blue
    SUCCESS = "#16a34a"  # Green
    WARNING = "#ea580c"  # Orange
    ERROR = "#ff4040"  # Red
    INFO = "#0891b2"  # Cyan

    # Text colors
    TEXT_PRIMARY = "#ffffff"  # White
    TEXT_SECONDARY = "#9ca3af"  # Gray
    TEXT_ACCENT = "#60a5fa"  # Light blue
    TEXT_MUTED = "#6b7280"  # Dark gray

    # UI elements
    BORDER = "#374151"  # Dark gray for borders
    BACKGROUND = "#111827"  # Dark background
    VOICE_ACTIVE = "#10b981"  # Green for voice activity
    AI_RESPONSE = "#8b5cf6"  # Purple for AI responses


class SamvaadInterface:
    """Main CLI interface for Samvaad with rich terminal UI."""

    def __init__(self):
        self.console = Console(file=sys.__stdout__)
        self.conversation_active = False
        self.conversation_manager = None
        self._should_exit = False  # Flag to control exit
        self.session_stats = {
            "messages": 0,
            "start_time": None,
            "voice_queries": 0,
            "text_queries": 0,
        }

        # Initialize prompt session with completions
        self.setup_completions()

    def get_terminal_width(self):
        """Get current terminal width for responsive design."""
        return self.console.size.width

    def get_responsive_panel_width(self, max_width_percent=0.9):
        """Calculate responsive panel width based on terminal size."""
        terminal_width = self.get_terminal_width()
        return min(
            int(terminal_width * max_width_percent), terminal_width - 4
        )  # Leave some margin

    def setup_completions(self):
        """Set up tab completion for commands."""
        from prompt_toolkit.completion import Completer, Completion

        class SlashCommandCompleter(Completer):
            def __init__(self, commands):
                self.commands = commands

            def get_completions(self, document, complete_event):
                # Only provide completions if the input starts with "/"
                text = document.text_before_cursor
                if not text.startswith("/"):
                    return

                # Find matching commands
                for cmd in self.commands:
                    if cmd.startswith(text):
                        yield Completion(cmd, start_position=-len(text))

        commands = [
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
        self.completer = SlashCommandCompleter(commands)
        # Create prompt session without custom key bindings to allow natural Ctrl+C handling
        self.prompt_session = PromptSession(completer=self.completer)

    def display_banner(self):
        """Display startup banner with ASCII art."""
        # Check terminal width for responsive design
        terminal_width = self.console.size.width

        if terminal_width >= 75:
            # Full ASCII art for wide terminals
            ascii_art = """
╭─────────────────────────────────────────────────────────────────────────╮
│   ███████╗ █████╗ ███╗   ███╗██╗   ██╗ █████╗  █████╗ ██████╗           │
│   ██╔════╝██╔══██╗████╗ ████║██║   ██║██╔══██╗██╔══██╗██╔══██╗          │
│   ███████╗███████║██╔████╔██║██║   ██║███████║███████║██║  ██║          │
│   ╚════██║██╔══██║██║╚██╔╝██║╚██╗ ██╔╝██╔══██║██╔══██║██║  ██║          │
│   ███████║██║  ██║██║ ╚═╝ ██║ ╚████╔╝ ██║  ██║██║  ██║██████╔╝          │
│   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝           │
│                                                                         │
│           Facilitating Dialogue-Based Learning Through AI               │
│                                                                         │
│     🗣️  Voice-First  •  📚 Document-Aware  •  🤖 AI-Powered             │
╰─────────────────────────────────────────────────────────────────────────╯
"""
        else:
            # Compact banner for narrow terminals
            ascii_art = """
╭─────────────────────────────────────────╮
│  ███████╗ █████╗ ███╗   ███╗            │
│  ██╔════╝██╔══██╗████╗ ████║            │
│  ███████╗███████║██╔████╔██║            │
│  ╚════██║██╔══██║██║╚██╔╝██║            │
│  ███████║██║  ██║██║ ╚═╝ ██║            │
│  ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝            │
│                                         │
│  🎙️ Samvaad - AI Assistant with Voice   │
╰─────────────────────────────────────────╯
"""

        # Display the ASCII art with beautiful gradient colors.
        # Print border characters (corners and vertical bars) with a consistent
        # border color, and print the interior content with the intended
        # gradient / accent styles so the outline remains uniform.
        lines = ascii_art.strip().split("\n")
        for i, line in enumerate(lines):
            # Corner-only lines (top/bottom) - print full line as border
            if line.startswith(("╭", "╰", "╮", "╯")):
                self.console.print(line, style=Colors.BORDER)
                continue

            # Lines with vertical borders and interior content
            if line.startswith("│") and line.endswith("│"):
                left_border = line[0]
                inner = line[1:-1]
                right_border = line[-1]

                # Decide the interior style (preserve previous gradient logic)
                if "███" in inner:  # SAMVAAD text lines
                    if i == 1:  # First line - brightest blue
                        inner_style = f"bold {Colors.PRIMARY}"
                    elif i == 2:  # Second line - medium blue
                        inner_style = f"bold #3b82f6"
                    elif i == 3:  # Third line - bright blue
                        inner_style = f"bold {Colors.TEXT_ACCENT}"
                    elif i == 4:  # Fourth line - medium blue
                        inner_style = f"bold #3b82f6"
                    elif i == 5:  # Fifth line - primary blue
                        inner_style = f"bold {Colors.PRIMARY}"
                    else:
                        inner_style = f"bold {Colors.PRIMARY}"
                elif "🎙️" in inner:  # Subtitle with voice emoji
                    inner_style = f"bold {Colors.SUCCESS}"
                elif "🗣️" in inner or "Voice-First" in inner:  # Feature line
                    inner_style = Colors.TEXT_ACCENT
                elif "Facilitating" in inner:  # Tagline - use normal text
                    inner_style = Colors.TEXT_PRIMARY
                else:
                    # Default interior text color
                    inner_style = Colors.TEXT_PRIMARY

                # Print left border, interior, and right border with correct styles
                self.console.print(left_border, style=Colors.BORDER, end="")
                self.console.print(inner, style=inner_style, end="")
                self.console.print(right_border, style=Colors.BORDER)
                continue

            # Fallback: print the whole line as border (safe default)
            self.console.print(line, style=Colors.BORDER)

        self.console.print()

    def display_help(self):
        """Display help information similar to Copilot CLI help."""
        help_text = """
# Available Commands

## Core Commands
- **Start conversation**: Just type your message or question and press enter
- **/voice** (/v) - Switch to continuous voice conversation mode for hands-free interaction
- **/text** (/t) - Switch back to text-only mode

## Document Management
- **/ingest <file_path>** (/i) - Ingest documents for Q&A (supports multiple files, folders, and glob patterns)
  - Examples: `/ingest document.pdf`, `/i document.pdf`, `/ingest *.txt`, `/ingest folder/`, `/ingest file1.pdf file2.txt`
- **/remove <file_path>** (/rm) - Remove ingested documents from knowledge base
  - Examples: `/remove document.pdf`, `/rm document.pdf`, `/remove *.txt`, `/remove folder`, `/remove file1.pdf file2.txt`

## Conversation Management
- **/clear** (/c) - Clear conversation history and start fresh
- **/status** (/s, /stat) - Show current session statistics

## Information & Help
- **/help** (/h) - Show this help message
- **/settings** (/cfg) - View current configuration

## Exit Commands
- **/quit** (/q) or **/exit** - Exit Samvaad
- **Ctrl+C** or **Ctrl+D** - Quick exit

## Tips
- Type naturally - no special formatting needed
- Use /voice for hands-free conversations
- Use /ingest to add documents, /remove to delete them
- Commands start with / (slash), aliases shown in parentheses
"""

    def display_help(self):
        """Display help information similar to Copilot CLI help."""
        # Check terminal width for fixed design
        terminal_width = self.console.size.width

        if terminal_width >= 75:
            # Full help panel for wide terminals
            panel_width = 75
        else:
            # Compact help panel for narrow terminals
            panel_width = 60

        help_text = """
# Available Commands

## Core Commands
- **Start conversation**: Just type your message or question and press enter
- **/voice** (/v) - Switch to continuous voice conversation mode for hands-free interaction
- **/text** (/t) - Switch back to text-only mode

## Document Management
- **/ingest <file_path>** (/i) - Ingest documents for Q&A (supports multiple files, folders, and glob patterns)
  - Examples: `/ingest document.pdf`, `/i document.pdf`, `/ingest *.txt`, `/ingest folder/`, `/ingest file1.pdf file2.txt`
- **/remove <file_path>** (/rm) - Remove ingested documents from knowledge base
  - Examples: `/remove document.pdf`, `/rm document.pdf`, `/remove *.txt`, `/remove folder/`, `/remove file1.pdf file2.txt`

## Conversation Management
- **/clear** (/c) - Clear conversation history and start fresh
- **/status** (/s, /stat) - Show current session statistics

## Information & Help
- **/help** (/h) - Show this help message
- **/settings** (/cfg) - View current configuration

## Exit Commands
- **/quit** (/q) or **/exit** - Exit Samvaad
- **Ctrl+C** or **Ctrl+D** - Quick exit

## Tips
- Type naturally - no special formatting needed
- Use /voice for hands-free conversations
- Use /ingest to add documents, /remove to delete them
- Commands start with / (slash), aliases shown in parentheses
"""

        markdown = Markdown(help_text)
        help_panel = Panel(
            markdown,
            title="[bold]Samvaad Help[/bold]",
            border_style=Colors.INFO,
            box=box.ROUNDED,
            width=panel_width,
        )

        self.console.print(help_panel)

    def display_status(self):
        """Display current session status."""
        if self.session_stats["start_time"]:
            duration = time.time() - self.session_stats["start_time"]
            duration_str = f"{int(duration // 60)}m {int(duration % 60)}s"
        else:
            duration_str = "0s"

        # Check terminal width for fixed design
        terminal_width = self.console.size.width

        if terminal_width >= 75:
            # Full status panel for wide terminals
            panel_width = 75
        else:
            # Compact status panel for narrow terminals
            panel_width = 60

        status_table = Table(title="Session Status", box=box.ROUNDED)
        status_table.add_column("Metric", style=Colors.TEXT_ACCENT)
        status_table.add_column("Value", style=Colors.TEXT_PRIMARY)

        status_table.add_row("Session Duration", duration_str)
        status_table.add_row("Total Messages", str(self.session_stats["messages"]))
        status_table.add_row("Voice Queries", str(self.session_stats["voice_queries"]))
        status_table.add_row("Text Queries", str(self.session_stats["text_queries"]))
        status_table.add_row(
            "Conversation Active", "✅ Yes" if self.conversation_active else "❌ No"
        )

        # Wrap table in a panel with fixed width
        status_panel = Panel(
            status_table, border_style=Colors.INFO, box=box.ROUNDED, width=panel_width
        )

        self.console.print(status_panel)

    def display_welcome(self):
        """Display welcome message with getting started tips."""
        # Check terminal width for fixed design like the banner
        terminal_width = self.console.size.width

        if terminal_width >= 75:
            # Full welcome panel for wide terminals (matching banner width)
            panel_width = 75
        else:
            # Compact welcome panel for narrow terminals
            panel_width = 60

        welcome_text = Text()
        welcome_text.append("Welcome to Samvaad! \n", style=f"bold {Colors.SUCCESS}")

        # Supported file types
        file_types_text = Text()
        file_types_text.append(
            "\nSupported file types: ", style=f"bold {Colors.TEXT_ACCENT}"
        )
        file_types_text.append("PDF", style=Colors.TEXT_SECONDARY)
        file_types_text.append(", Office docs ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("(.docx, .pptx, .xlsx)", style=Colors.TEXT_MUTED)
        file_types_text.append(", Text ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("(.txt, .md)", style=Colors.TEXT_MUTED)
        file_types_text.append(", ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("Web pages ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("(.html, .htm)", style=Colors.TEXT_MUTED)
        file_types_text.append(", Images ", style=Colors.TEXT_SECONDARY)
        file_types_text.append(
            "(.png, .jpg, .jpeg, .tiff, .bmp)", style=Colors.TEXT_MUTED
        )
        file_types_text.append(" with OCR, ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("and other formats ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("(.rtf, .epub)", style=Colors.TEXT_MUTED)
        file_types_text.append("\n\n", style=Colors.TEXT_SECONDARY)

        # Quick start commands
        commands_text = Text()
        commands_text.append("• ", style=Colors.TEXT_MUTED)
        commands_text.append("Type ", style=Colors.TEXT_SECONDARY)
        commands_text.append("/voice", style=f"bold {Colors.VOICE_ACTIVE}")
        commands_text.append(
            " for continuous voice conversation\n", style=Colors.TEXT_SECONDARY
        )

        commands_text.append("• ", style=Colors.TEXT_MUTED)
        commands_text.append("Type ", style=Colors.TEXT_SECONDARY)
        commands_text.append("/ingest <file>", style=f"bold {Colors.INFO}")
        commands_text.append(" to add documents for Q&A\n", style=Colors.TEXT_SECONDARY)

        commands_text.append("• ", style=Colors.TEXT_MUTED)
        commands_text.append("Type ", style=Colors.TEXT_SECONDARY)
        commands_text.append("/remove <file>", style=f"bold {Colors.WARNING}")
        commands_text.append(" to remove documents\n", style=Colors.TEXT_SECONDARY)

        commands_text.append("• ", style=Colors.TEXT_MUTED)
        commands_text.append("Type ", style=Colors.TEXT_SECONDARY)
        commands_text.append("/help", style=f"bold {Colors.INFO}")
        commands_text.append(
            " to see all available commands\n", style=Colors.TEXT_SECONDARY
        )

        commands_text.append("• ", style=Colors.TEXT_MUTED)
        commands_text.append(
            "Start typing to get textual answers about your documents!\n",
            style=Colors.TEXT_SECONDARY,
        )

        commands_text.append(
            "\nFirst cold start may take a few seconds as models load. Please be patient :)\n",
            style=Colors.TEXT_MUTED,
        )

        welcome_panel = Panel(
            welcome_text + file_types_text + commands_text,
            border_style=Colors.SUCCESS,
            box=box.ROUNDED,
            padding=(1, 2),
            width=panel_width,
        )

        self.console.print(welcome_panel)

    def show_thinking_indicator(self, message: str = "Thinking..."):
        """Show a thinking/processing indicator."""
        with console.status(f"[bold blue]{message}[/bold blue]", spinner="dots"):
            time.sleep(0.5)  # Brief pause for visual feedback

    def format_ai_response(
        self, response: str, sources: List[Dict] = None, query_time: float = None
    ):
        """Format AI response with proper styling and enhanced information."""
        # Check terminal width for fixed design
        terminal_width = self.console.size.width

        if terminal_width >= 75:
            # Full response panel for wide terminals
            panel_width = 75
        else:
            # Compact response panel for narrow terminals
            panel_width = 60

        # Create response content
        response_content = Text()
        response_content.append(response, style=Colors.TEXT_PRIMARY)

        # Add query timing if available
        if query_time:
            response_content.append(
                f"\n\n⏱️  Response generated in {query_time:.2f}s",
                style=Colors.TEXT_MUTED,
            )

        # Create the main response panel
        response_panel = Panel(
            response_content,
            title="[bold]Response[/bold]",
            title_align="left",
            border_style=Colors.AI_RESPONSE,
            box=box.ROUNDED,
            padding=(1, 2),
            width=panel_width,
        )

        self.console.print(response_panel)

        # TODO: Add sources display back later
        # Enhanced sources display
        # if sources and len(sources) > 0:
        #     # Create sources table
        #     sources_table = Table(
        #         title=f"📚 Sources ({len(sources)} documents referenced)",
        #         box=box.SIMPLE,
        #         show_header=True,
        #         header_style=Colors.TEXT_ACCENT
        #     )
        #     sources_table.add_column("Document", style=Colors.TEXT_PRIMARY, width=min(30, self.get_terminal_width() // 4))
        #     sources_table.add_column("Relevance", style=Colors.SUCCESS, width=min(12, self.get_terminal_width() // 8))
        #     sources_table.add_column("Preview", style=Colors.TEXT_SECONDARY, width=min(50, self.get_terminal_width() // 3))
        #
        #     for i, source in enumerate(sources[:3]):  # Show top 3 sources
        #         doc_name = source.get('metadata', {}).get('filename', 'Unknown')
        #         similarity = source.get('similarity', 0.0)
        #         preview = source.get('content', '')[:100] + "..." if len(source.get('content', '')) > 100 else source.get('content', '')
        #
        #         sources_table.add_row(
        #             doc_name,
        #             f"{similarity:.1%}" if similarity else "N/A",
        #             preview
        #         )
        #
        #     # Wrap sources table in responsive panel
        #     sources_panel = Panel(
        #         sources_table,
        #         border_style=Colors.TEXT_MUTED,
        #         box=box.ROUNDED,
        #         width=self.get_responsive_panel_width()
        #     )
        #     self.console.print(sources_panel)
        # else:
        #     # No sources message
        #     no_sources = Text("💡 ", style=Colors.TEXT_MUTED)
        #     no_sources.append("Response generated from general knowledge", style=Colors.TEXT_MUTED)
        #     self.console.print(no_sources)

    def format_user_message(self, message: str, mode: str = "text"):
        """Format user message with appropriate styling."""
        if mode == "voice":
            prefix = "🎙️ "
            style = Colors.VOICE_ACTIVE
        else:
            prefix = "📝 "
            style = Colors.TEXT_ACCENT

        user_text = Text()
        user_text.append(prefix, style=style)
        user_text.append(message, style=Colors.TEXT_PRIMARY)

        self.console.print(user_text)

    def handle_slash_command(self, command: str) -> bool:
        """Handle slash commands. Returns True if should continue, False to exit."""
        # Parse command arguments
        parts = command.strip().split()
        if not parts:
            return True

        cmd = parts[0].lower()
        original_command = command.strip()

        if cmd in ["/help", "/h"]:
            self.display_help()

        elif cmd in ["/status", "/stat", "/s"]:
            self.display_status()

        elif cmd in ["/voice", "/v"]:
            self.start_voice_mode()

        elif cmd in ["/text", "/t"]:
            self.console.print("📝 Switched to text mode", style=Colors.SUCCESS)

        elif cmd in ["/ingest", "/i"]:
            self.handle_ingest_command(original_command)

        elif cmd in ["/remove", "/rm"]:
            self.handle_remove_command(original_command)

        elif cmd in ["/settings", "/config", "/cfg"]:
            self.show_settings()

        elif cmd in ["/quit", "/exit", "/q"]:
            return False

        else:
            self.console.print(f"❓ Unknown command: {parts[0]}", style=Colors.WARNING)
            self.console.print(
                "Type /help to see available commands", style=Colors.TEXT_MUTED
            )

        return True

    def show_settings(self):
        """Display current settings."""
        # Check terminal width for fixed design
        terminal_width = self.console.size.width

        if terminal_width >= 75:
            # Full settings panel for wide terminals
            panel_width = 75
        else:
            # Compact settings panel for narrow terminals
            panel_width = 60

        settings_table = Table(title="Current Settings", box=box.ROUNDED)
        settings_table.add_column("Setting", style=Colors.TEXT_ACCENT)
        settings_table.add_column("Value", style=Colors.TEXT_PRIMARY)

        # TODO: Get actual settings from conversation manager
        settings_table.add_row("Model", "llama-3.3-70b-versatile")
        settings_table.add_row("Language", "English")
        settings_table.add_row("Voice Mode", "Available")
        settings_table.add_row("Max History", "50 messages")

        # Wrap table in a panel with fixed width
        settings_panel = Panel(
            settings_table, border_style=Colors.INFO, box=box.ROUNDED, width=panel_width
        )

        self.console.print(settings_panel)

    def handle_ingest_command(self, command: str):
        """Handle document ingestion command."""
        # Parse command arguments
        parts = command.split()
        if len(parts) < 2:
            self.console.print(
                "❌ Usage: /ingest <file_or_folder> [file_or_folder2 ...]",
                style=Colors.ERROR,
            )
            self.console.print("Examples:", style=Colors.TEXT_MUTED)
            self.console.print("  /ingest document.pdf", style=Colors.TEXT_MUTED)
            self.console.print("  /ingest folder_name", style=Colors.TEXT_MUTED)
            self.console.print("  /ingest file1.pdf file2.txt", style=Colors.TEXT_MUTED)
            return

        # Show loading progress bar for ingestion dependencies
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            load_task = progress.add_task(
                "[cyan]Loading ingestion dependencies...", total=None
            )

            try:
                # Import heavy ingestion modules here to show loading progress
                from samvaad.pipeline.ingestion.chunking import chunk_text, parse_file
                from samvaad.pipeline.ingestion.embedding import generate_embeddings
                from samvaad.pipeline.ingestion.ingestion import (
                    ingest_file_pipeline_with_progress,
                )
                from samvaad.utils.hashing import generate_file_id

                # Mark loading complete
                progress.update(load_task, completed=True, visible=False)

            except Exception as e:
                progress.update(load_task, visible=False)
                self.console.print(
                    f"❌ Error loading ingestion dependencies: {e}", style=Colors.ERROR
                )
                return

        # Show immediate progress for setup work
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            setup_task = progress.add_task(
                "[cyan]Preparing files for ingestion...", total=None
            )

            # Get file paths from command
            file_paths = parts[1:]

            # Expand glob patterns and resolve paths
            expanded_paths = []
            for path in file_paths:
                # Expand glob patterns
                matches = glob.glob(path)
                if matches:
                    expanded_paths.extend(matches)
                else:
                    # If no glob matches, try common locations
                    possible_paths = [
                        path,  # As given
                        f"data/documents/{path}",  # In documents directory
                        f"./{path}",  # Explicit relative
                    ]

                    found = False
                    for possible_path in possible_paths:
                        if os.path.exists(possible_path):
                            if os.path.isfile(possible_path):
                                expanded_paths.append(possible_path)
                                found = True
                                break
                            elif os.path.isdir(possible_path):
                                # If it's a directory, add all files in it
                                for root, dirs, files in os.walk(possible_path):
                                    for file in files:
                                        expanded_paths.append(os.path.join(root, file))
                                found = True
                                break

                    if not found:
                        # If still not found, treat as literal path for error reporting
                        expanded_paths.append(path)

            # Filter to existing files
            valid_files = []
            for path in expanded_paths:
                if os.path.isfile(path):
                    valid_files.append(path)
                elif os.path.isdir(path):
                    # Recursively find all files in directory
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            valid_files.append(os.path.join(root, file))
                else:
                    # Try one more time with data/documents prefix for better error messages
                    alt_path = f"data/documents/{os.path.basename(path)}"
                    if os.path.isfile(alt_path):
                        self.console.print(
                            f"💡 Did you mean: /ingest {alt_path}", style=Colors.INFO
                        )
                    self.console.print(
                        f"⚠️  Path not found: {path}", style=Colors.WARNING
                    )

            if not valid_files:
                progress.update(setup_task, visible=False)
                self.console.print(
                    "❌ No valid files found to ingest", style=Colors.ERROR
                )
                self.console.print(
                    "💡 Try: /ingest data/documents/filename.pdf",
                    style=Colors.TEXT_MUTED,
                )
                return

            # Mark setup complete and show file count
            progress.update(setup_task, completed=True, visible=False)

        self.console.print(
            f"Found {len(valid_files)} file(s) to process", style=Colors.INFO
        )

        # Process files with detailed progress tracking
        successful = 0
        failed = 0
        unchanged = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            main_task = progress.add_task(
                f"[cyan]Processing {len(valid_files)} file(s)...",
                total=len(valid_files),
            )

            for i, file_path in enumerate(valid_files):
                filename = os.path.basename(file_path)
                self.console.print(
                    f"\nStarting {filename} ingestion", style=Colors.TEXT_PRIMARY
                )
                progress.update(
                    main_task, description="[cyan]Reading file...", refresh=True
                )

                try:
                    # Read file
                    with open(file_path, "rb") as f:
                        contents = f.read()

                    # Determine content type
                    import mimetypes

                    content_type, _ = mimetypes.guess_type(file_path)
                    if not content_type:
                        content_type = "application/octet-stream"

                    progress.update(
                        main_task, description="[cyan]Parsing file...", refresh=True
                    )

                    # Suppress all logging during ingestion
                    import logging
                    import sys
                    from io import StringIO

                    # Save original handlers
                    logging.disable(logging.CRITICAL)
                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = StringIO()
                    sys.stderr = StringIO()

                    try:
                        # Process the file through the ingestion pipeline with detailed progress
                        def progress_callback(
                            step: str, current: int = None, total: int = None
                        ):
                            suffix = ""
                            progress.update(
                                main_task,
                                description=f"[cyan]{step}{suffix}",
                                refresh=True,
                            )

                        result = ingest_file_pipeline_with_progress(
                            filename=filename,
                            content_type=content_type,
                            contents=contents,
                            progress_callback=progress_callback,
                        )

                        # Add small delay to allow spinner animation
                        import time

                        time.sleep(0.05)

                    finally:
                        # Restore logging and output
                        logging.disable(logging.NOTSET)
                        sys.stdout = old_stdout
                        sys.stderr = old_stderr

                    if result.get("error"):
                        err = result["error"]
                        # Treat already-processed/no-new-chunks/no-new-embeddings as 'unchanged'
                        if err in (
                            "File already processed",
                            "No new chunks to process",
                            "No new embeddings",
                        ):
                            self.console.print(
                                f"Skipped {filename}: {err}", style=Colors.TEXT_MUTED
                            )
                            unchanged += 1
                        else:
                            self.console.print(
                                f"❌ Failed to ingest {filename}: {err}",
                                style=Colors.ERROR,
                            )
                            failed += 1
                    else:
                        chunks = result.get("num_chunks", 0)
                        new_chunks = result.get("new_chunks_embedded", 0)
                        self.console.print(
                            f"Ingested {filename}: {chunks} chunks, {new_chunks} new",
                            style=Colors.TEXT_PRIMARY,
                        )
                        successful += 1

                except Exception as e:
                    self.console.print(
                        f"❌ Error processing {filename}: {e}", style=Colors.ERROR
                    )
                    failed += 1

                # Update progress
                progress.update(main_task, advance=1, refresh=True)

        # Summary
        # Final summary: include unchanged (skipped) files
        summary_style = Colors.SUCCESS if failed == 0 else Colors.WARNING
        self.console.print(
            f"\nIngestion complete: {successful} successful, {failed} failed, {unchanged} unchanged",
            style=summary_style,
        )

    def handle_remove_command(self, command: str):
        """Handle document removal command."""
        # Parse command arguments
        parts = command.split()
        if len(parts) < 2:
            self.console.print(
                "❌ Usage: /remove <file_or_folder> [file_or_folder2 ...]",
                style=Colors.ERROR,
            )
            self.console.print("Examples:", style=Colors.TEXT_MUTED)
            self.console.print("  /remove document.pdf", style=Colors.TEXT_MUTED)
            self.console.print("  /remove folder_name", style=Colors.TEXT_MUTED)
            self.console.print("  /remove file1.pdf file2.txt", style=Colors.TEXT_MUTED)
            return

        # Get file/folder paths from command
        file_patterns = parts[1:]

        # Collect all files to remove (get basenames from disk)
        files_to_remove = set()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            setup_task = progress.add_task(
                "[cyan]Collecting files to remove...", total=None
            )

            for pattern in file_patterns:
                # Try to find the path
                possible_paths = [
                    pattern,
                    f"data/documents/{pattern}",
                    f"./{pattern}",
                ]

                found_path = None
                for possible_path in possible_paths:
                    if os.path.exists(possible_path):
                        found_path = possible_path
                        break

                if found_path:
                    if os.path.isdir(found_path):
                        # Recursively collect all files from directory
                        for root, dirs, files in os.walk(found_path):
                            for file in files:
                                files_to_remove.add(file)
                    elif os.path.isfile(found_path):
                        # Single file
                        files_to_remove.add(os.path.basename(found_path))
                else:
                    # Path doesn't exist on disk - still try to remove by basename
                    files_to_remove.add(os.path.basename(pattern))

            progress.update(setup_task, visible=False)

        if not files_to_remove:
            self.console.print("ℹNo files found to remove", style=Colors.INFO)
            return

        # Note: CLI file removal is deprecated. Use the web UI or API to delete files.
        # This CLI command requires user_id which isn't available in standalone CLI mode.
        self.console.print(
            "⚠️  File removal is only supported via the web UI or API.",
            style=Colors.WARNING
        )
        self.console.print(
            "   Use the Knowledge Base panel to delete files.",
            style=Colors.INFO
        )
        return
        
        # Legacy code below kept for reference
        all_matches = []

        if not all_matches:
            self.console.print("No matching files found in database", style=Colors.INFO)
            return

        # Remove files with progress bar
        removed_files = 0
        removed_chunks = 0
        failed = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            main_task = progress.add_task(
                f"[cyan]Removing {len(all_matches)} file(s)...", total=len(all_matches)
            )

            for file_id, stored_filename in all_matches:
                try:
                    orphaned_chunks = delete_file_and_cleanup(file_id)
                    if orphaned_chunks:
                        removed_chunks += len(orphaned_chunks)

                    removed_files += 1
                    self.console.print(
                        f"Removed {stored_filename}", style=Colors.TEXT_PRIMARY
                    )
                except Exception as e:
                    failed += 1
                    self.console.print(
                        f"Failed to remove {stored_filename}: {e}", style=Colors.ERROR
                    )

                progress.update(main_task, advance=1)

        # Final summary only
        if removed_files > 0:
            self.console.print(
                f"Removed {removed_files} file(s), {removed_chunks} chunks deleted",
                style=Colors.SUCCESS,
            )
        else:
            self.console.print("No matching files found to remove", style=Colors.INFO)

    def start_voice_mode(self):
        """Start voice conversation mode with immediate progress feedback."""
        self.console.print("Starting voice mode...", style=Colors.VOICE_ACTIVE)

        # Use a progress bar to cover the entire initialization, including heavy imports
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            # Task for initial setup (imports and component init)
            init_task = progress.add_task(
                "[cyan]Initializing voice components...", total=None
            )

            try:
                # Suppress warnings before importing voice libraries
                import warnings

                warnings.filterwarnings("ignore", category=UserWarning)
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                warnings.filterwarnings("ignore", message=".*pkg_resources.*")
                warnings.filterwarnings("ignore", message=".*deprecated.*")

                # Heavy imports are now inside the progress bar context
                import sounddevice
                import webrtcvad
                from faster_whisper import WhisperModel

                # Initialize conversation components
                self.init_conversation_components()

                # Mark initial setup as complete
                progress.update(init_task, completed=True, visible=False)

                # --- Model Loading with Individual Progress ---

                # Suppress all stdout during model loading to hide library messages
                import sys
                from io import StringIO

                old_stdout = sys.stdout
                sys.stdout = StringIO()

            except (ImportError, RuntimeError) as e:
                # If any part of initialization fails, hide progress and show error
                progress.update(init_task, visible=False)
                self.console.print(
                    f"❌ Voice mode unavailable: {e}", style=Colors.ERROR
                )
                self.console.print(
                    "Voice mode has been migrated to WebRTC. Use the API for voice interactions.",
                    style=Colors.TEXT_MUTED,
                )
                return

        # Voice mode is no longer available in CLI - migrated to WebRTC

    def init_conversation_components(self):
        """Initialize conversation manager and loop."""
        try:
            # Import conversation components - using basic manager since voice mode removed
            from samvaad.pipeline.retrieval.query import ConversationManager

            # Initialize conversation manager if not already done
            if not self.conversation_manager:
                self.conversation_manager = ConversationManager()

        except Exception as e:
            self.console.print(
                f"❌ Failed to initialize conversation components: {e}",
                style=Colors.ERROR,
            )

    def process_text_query(self, query: str):
        """Process a text query through the RAG pipeline."""
        query_start_time = time.time()

        # Show immediate progress for setup work
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            setup_task = progress.add_task(
                "[cyan]Preparing query processing...", total=None
            )

            try:
                # Initialize conversation components if needed
                if not self.conversation_manager:
                    self.init_conversation_components()

                # Import query pipeline
                from samvaad.pipeline.retrieval.query import rag_query_pipeline

                # Mark setup complete
                progress.update(setup_task, completed=True, visible=False)

            except Exception as e:
                progress.update(setup_task, visible=False)
                self.console.print(
                    f"❌ Error initializing query processing: {e}", style=Colors.ERROR
                )
                return {
                    "answer": f"Sorry, I encountered an error: {e}",
                    "success": False,
                    "sources": [],
                }

        # Enhanced query processing with detailed steps
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            # Multi-step progress tracking
            search_task = progress.add_task("[cyan]Searching documents...", total=None)

            try:
                # Process the query
                result = rag_query_pipeline(
                    query,
                    model="llama-3.3-70b-versatile",
                    conversation_manager=self.conversation_manager,
                )

                # Update to generation phase
                progress.update(search_task, description="[cyan]Generating response...")

                # Small delay to show the generation message
                time.sleep(0.1)

                # Mark as complete
                progress.update(search_task, completed=True, visible=False)

                # Calculate total time
                query_time = time.time() - query_start_time
                result["query_time"] = query_time

                # Update stats
                self.session_stats["messages"] += 1
                self.session_stats["text_queries"] += 1

                return result

            except Exception as e:
                # Hide progress on error
                progress.update(search_task, visible=False)

                self.console.print(
                    f"❌ Error processing query: {e}", style=Colors.ERROR
                )
                return {
                    "answer": f"Sorry, I encountered an error: {e}",
                    "success": False,
                    "sources": [],
                    "query_time": time.time() - query_start_time,
                }

    def run_interactive_loop(self):
        """Main interactive loop for text-based conversation."""
        try:
            while not self._should_exit:
                try:
                    # Get user input with rich prompt
                    user_input = self.prompt_session.prompt(
                        HTML("<ansicyan>❯ </ansicyan>"), multiline=False
                    )

                    # Handle None or empty input
                    if user_input is None or self._should_exit:
                        break

                    user_input = user_input.strip()
                    if not user_input:
                        continue

                    # Handle slash commands
                    if user_input.startswith("/"):
                        if not self.handle_slash_command(user_input):
                            break
                        continue

                    # Process query and get response
                    result = self.process_text_query(user_input)

                    # Display AI response with enhanced formatting
                    if result and result.get("answer"):
                        self.format_ai_response(
                            result["answer"],
                            result.get("sources", []),
                            result.get("query_time"),
                        )

                    self.console.print()  # Add spacing

                except KeyboardInterrupt:
                    self.console.print("\n👋 Goodbye!", style=Colors.SUCCESS)
                    break
                except EOFError:
                    break

        except Exception as e:
            self.console.print(f"❌ Unexpected error: {e}", style=Colors.ERROR)

    def start(self):
        """Start the Samvaad CLI interface."""
        # Record session start time
        self.session_stats["start_time"] = time.time()

        # Clear screen and show banner
        self.console.clear()
        self.display_banner()
        self.display_welcome()

        # Start interactive loop
        self.run_interactive_loop()


def main():
    """Main entry point for the Samvaad CLI."""

    # Handle command line arguments
    @click.command()
    @click.option("--help-cmd", "--help", is_flag=True, help="Show help and exit")
    @click.version_option(version="0.1.0", prog_name="Samvaad")
    def cli(help_cmd):
        """
        🎙️ Samvaad - AI Conversational Assistant

        An intelligent assistant that understands text queries, with document awareness
        and contextual conversations powered by advanced AI models.

        Examples:

        \b
        samvaad                 # Start interactive mode
        samvaad --help          # Show this help
        """
        if help_cmd:
            ctx = click.get_current_context()
            click.echo(ctx.get_help())
            return

        try:
            # Initialize and start the interface
            interface = SamvaadInterface()

            # Start in normal interactive mode
            interface.start()

        except KeyboardInterrupt:
            console.print("\n👋 Shutting down gracefully...", style=Colors.SUCCESS)
        except Exception as e:
            console.print(f"\n❌ Unexpected error: {e}", style=Colors.ERROR)
        finally:
            sys.exit(0)

    # Start the CLI
    cli()


if __name__ == "__main__":
    main()
