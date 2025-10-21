"""
Main CLI interface for Samvaad - inspired by GitHub Copilot CLI and Gemini CLI design patterns.
"""

import os
import sys
import time
import signal
import asyncio
import glob
from typing import Optional, Dict, Any, List
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
import sqlite3
from rich.layout import Layout
from rich.live import Live
from rich import box
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.formatted_text import HTML

# Initialize console for rich output
console = Console()

# Color scheme inspired by GitHub Copilot CLI and Gemini CLI
class Colors:
    # System colors
    PRIMARY = "#2563eb"      # Blue
    SUCCESS = "#16a34a"      # Green  
    WARNING = "#ea580c"      # Orange
    ERROR = "#dc2626"        # Red
    INFO = "#0891b2"         # Cyan
    
    # Text colors
    TEXT_PRIMARY = "#ffffff"    # White
    TEXT_SECONDARY = "#9ca3af"  # Gray
    TEXT_ACCENT = "#60a5fa"     # Light blue
    TEXT_MUTED = "#6b7280"      # Dark gray
    
    # UI elements
    BORDER = "#374151"          # Dark gray for borders
    BACKGROUND = "#111827"      # Dark background
    VOICE_ACTIVE = "#10b981"    # Green for voice activity
    AI_RESPONSE = "#8b5cf6"     # Purple for AI responses

class SamvaadInterface:
    """Main CLI interface for Samvaad with rich terminal UI."""
    
    def __init__(self):
        self.console = Console()
        self.conversation_active = False
        self.conversation_manager = None
        self._should_exit = False  # Flag to control exit
        self.session_stats = {
            'messages': 0,
            'start_time': None,
            'voice_queries': 0,
            'text_queries': 0
        }
        
        # Initialize prompt session with completions
        self.setup_completions()
        
    def setup_completions(self):
        """Set up tab completion for commands."""
        from prompt_toolkit.completion import Completer, Completion
        
        class SlashCommandCompleter(Completer):
            def __init__(self, commands):
                self.commands = commands
                
            def get_completions(self, document, complete_event):
                # Only provide completions if the input starts with "/"
                text = document.text_before_cursor
                if not text.startswith('/'):
                    return
                    
                # Find matching commands
                for cmd in self.commands:
                    if cmd.startswith(text):
                        yield Completion(cmd, start_position=-len(text))
        
        commands = [
            '/help', '/h', '/voice', '/v', '/text', '/t',
            '/settings', '/cfg', '/quit', '/q', '/exit', '/status', '/s', '/stat',
            '/ingest', '/i', '/remove', '/rm'
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
        
        # Display the ASCII art with beautiful gradient colors
        lines = ascii_art.strip().split('\n')
        for i, line in enumerate(lines):
            if "╭" in line or "╰" in line or "│" in line[:3]:  # Borders
                if "███" in line:  # SAMVAAD text lines with special gradient
                    # Gradient effect for the ASCII letters
                    if i == 1:  # First line - brightest blue
                        self.console.print(line, style=f"bold {Colors.PRIMARY}")
                    elif i == 2:  # Second line - medium blue  
                        self.console.print(line, style=f"bold #3b82f6")
                    elif i == 3:  # Third line - bright blue
                        self.console.print(line, style=f"bold {Colors.TEXT_ACCENT}")
                    elif i == 4:  # Fourth line - medium blue
                        self.console.print(line, style=f"bold #3b82f6") 
                    elif i == 5:  # Fifth line - primary blue
                        self.console.print(line, style=f"bold {Colors.PRIMARY}")
                    else:
                        self.console.print(line, style=f"bold {Colors.PRIMARY}")
                elif "🎙️" in line:  # Subtitle with voice emoji
                    self.console.print(line, style=f"bold {Colors.SUCCESS}")
                elif "🗣️" in line or "Voice-First" in line:  # Feature line
                    self.console.print(line, style=Colors.TEXT_ACCENT)
                elif "Facilitating" in line:  # Tagline - use normal text
                    self.console.print(line, style=Colors.TEXT_PRIMARY)
                else:  # Regular border lines
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
            box=box.ROUNDED
        )
        
        self.console.print(help_panel)
        
    def display_status(self):
        """Display current session status."""
        if self.session_stats['start_time']:
            duration = time.time() - self.session_stats['start_time']
            duration_str = f"{int(duration//60)}m {int(duration%60)}s"
        else:
            duration_str = "0s"
            
        status_table = Table(title="Session Status", box=box.ROUNDED)
        status_table.add_column("Metric", style=Colors.TEXT_ACCENT)
        status_table.add_column("Value", style=Colors.TEXT_PRIMARY)
        
        status_table.add_row("Session Duration", duration_str)
        status_table.add_row("Total Messages", str(self.session_stats['messages']))
        status_table.add_row("Voice Queries", str(self.session_stats['voice_queries']))
        status_table.add_row("Text Queries", str(self.session_stats['text_queries']))
        status_table.add_row("Conversation Active", "✅ Yes" if self.conversation_active else "❌ No")
        
        self.console.print(status_table)
        
    def display_welcome(self):
        """Display welcome message with getting started tips."""
        welcome_text = Text()
        welcome_text.append("Welcome to Samvaad! \n", style=f"bold Colors.SUCCESS")
        
        # Supported file types
        file_types_text = Text()
        file_types_text.append("\nSupported file types: ", style=f"bold {Colors.TEXT_ACCENT}")
        file_types_text.append("PDF", style=Colors.TEXT_SECONDARY)
        file_types_text.append(", Office docs ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("(.docx, .pptx, .xlsx)", style=Colors.TEXT_MUTED)
        file_types_text.append(", Text ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("(.txt, .md)", style=Colors.TEXT_MUTED)
        file_types_text.append(", ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("Web pages ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("(.html, .htm)", style=Colors.TEXT_MUTED)
        file_types_text.append(", Images ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("(.png, .jpg, .jpeg, .tiff, .bmp)", style=Colors.TEXT_MUTED)
        file_types_text.append(" with OCR, ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("and other formats ", style=Colors.TEXT_SECONDARY)
        file_types_text.append("(.rtf, .epub)", style=Colors.TEXT_MUTED)
        file_types_text.append("\n\n", style=Colors.TEXT_SECONDARY)
        
        # Quick start commands
        commands_text = Text()
        commands_text.append("• ", style=Colors.TEXT_MUTED)
        commands_text.append("Type ", style=Colors.TEXT_SECONDARY)
        commands_text.append("/voice", style=f"bold {Colors.VOICE_ACTIVE}")
        commands_text.append(" for continuous voice conversation\n", style=Colors.TEXT_SECONDARY)
        
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
        commands_text.append(" to see all available commands\n", style=Colors.TEXT_SECONDARY)
        
        commands_text.append("• ", style=Colors.TEXT_MUTED)
        commands_text.append("Start typing to get textual answers about your documents!\n", style=Colors.TEXT_SECONDARY)

        commands_text.append("\nFirst cold start may take a few seconds as models load. Please be patient :)\n", style=Colors.TEXT_MUTED)
        
        welcome_panel = Panel(
            welcome_text + file_types_text + commands_text,
            border_style=Colors.SUCCESS,
            box=box.ROUNDED,
            padding=(1, 2)
        )
        
        self.console.print(welcome_panel)
        
    def show_thinking_indicator(self, message: str = "Thinking..."):
        """Show a thinking/processing indicator."""
        with console.status(f"[bold blue]{message}[/bold blue]", spinner="dots"):
            time.sleep(0.5)  # Brief pause for visual feedback
            
    def format_ai_response(self, response: str, sources: List[Dict] = None, query_time: float = None):
        """Format AI response with proper styling and enhanced information."""
        # Create response content
        response_content = Text()
        response_content.append(response, style=Colors.TEXT_PRIMARY)
        
        # Add query timing if available
        if query_time:
            response_content.append(f"\n\n⏱️  Response generated in {query_time:.2f}s", 
                                   style=Colors.TEXT_MUTED)
        
        # Create the main response panel
        response_panel = Panel(
            response_content,
            title="[bold]Response[/bold]",
            title_align="left", 
            border_style=Colors.AI_RESPONSE,
            box=box.ROUNDED,
            padding=(1, 2)
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
        #     sources_table.add_column("Document", style=Colors.TEXT_PRIMARY, width=30)
        #     sources_table.add_column("Relevance", style=Colors.SUCCESS, width=12)
        #     sources_table.add_column("Preview", style=Colors.TEXT_SECONDARY, width=50)
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
        #     self.console.print(sources_table)
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
        
        if cmd in ['/help', '/h']:
            self.display_help()
            
        elif cmd in ['/status', '/stat', '/s']:
            self.display_status()
            
        elif cmd in ['/voice', '/v']:
            self.start_voice_mode()
            
        elif cmd in ['/text', '/t']:
            self.console.print("📝 Switched to text mode", 
                             style=Colors.SUCCESS)
            
        elif cmd in ['/ingest', '/i']:
            self.handle_ingest_command(original_command)
            
        elif cmd in ['/remove', '/rm']:
            self.handle_remove_command(original_command)
            
        elif cmd in ['/settings', '/config', '/cfg']:
            self.show_settings()
            
        elif cmd in ['/quit', '/exit', '/q']:
            return False
            
        else:
            self.console.print(f"❓ Unknown command: {parts[0]}", 
                             style=Colors.WARNING)
            self.console.print("Type /help to see available commands", 
                             style=Colors.TEXT_MUTED)
            
        return True
        
    def show_settings(self):
        """Display current settings."""
        settings_table = Table(title="Current Settings", box=box.ROUNDED)
        settings_table.add_column("Setting", style=Colors.TEXT_ACCENT)
        settings_table.add_column("Value", style=Colors.TEXT_PRIMARY)
        
        # TODO: Get actual settings from conversation manager
        settings_table.add_row("Model", "gemini-2.5-flash")
        settings_table.add_row("Language", "English")
        settings_table.add_row("Voice Mode", "Available")
        settings_table.add_row("Max History", "50 messages")
        
        self.console.print(settings_table)
        
    def handle_ingest_command(self, command: str):
        """Handle document ingestion command."""
        # Parse command arguments
        parts = command.split()
        if len(parts) < 2:
            self.console.print("❌ Usage: /ingest <file_path> [file_path2 ...]", 
                             style=Colors.ERROR)
            self.console.print("Example: /ingest document.pdf", 
                             style=Colors.TEXT_MUTED)
            self.console.print("Example: /ingest data/documents/*.pdf", 
                             style=Colors.TEXT_MUTED)
            return
        
        # Show immediate progress for setup work
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            setup_task = progress.add_task("[cyan]Preparing files for ingestion...", total=None)
            
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
                        self.console.print(f"💡 Did you mean: /ingest {alt_path}", 
                                         style=Colors.INFO)
                    self.console.print(f"⚠️  Path not found: {path}", 
                                     style=Colors.WARNING)
            
            if not valid_files:
                progress.update(setup_task, visible=False)
                self.console.print("❌ No valid files found to ingest", 
                                 style=Colors.ERROR)
                self.console.print("💡 Try: /ingest data/documents/filename.pdf", 
                                 style=Colors.TEXT_MUTED)
                return
                
            # Mark setup complete and show file count
            progress.update(setup_task, completed=True, visible=False)
            
        self.console.print(f"📚 Found {len(valid_files)} file(s) to process", 
                         style=Colors.INFO)
        
        # Process files with progress bar that works with multiple files
        successful = 0
        failed = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("({task.completed}/{task.total})"),
            console=self.console
        ) as progress:
            main_task = progress.add_task(f"[cyan]Processing {len(valid_files)} file(s)...", total=len(valid_files))
            
            for i, file_path in enumerate(valid_files):
                # Update progress description for current file
                progress.update(main_task, description=f"[cyan]Processing {os.path.basename(file_path)}...")
                
                try:
                    # Read file
                    with open(file_path, 'rb') as f:
                        contents = f.read()
                    
                    # Determine content type
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(file_path)
                    if not content_type:
                        content_type = 'application/octet-stream'
                    
                    # Import ingestion pipeline
                    from samvaad.pipeline.ingestion.ingestion import ingest_file_pipeline
                    
                    # Process file
                    result = ingest_file_pipeline(
                        filename=os.path.basename(file_path),
                        content_type=content_type,
                        contents=contents
                    )
                    
                    if result.get('error'):
                        self.console.print(f"❌ Failed to ingest {os.path.basename(file_path)}: {result['error']}", 
                                         style=Colors.ERROR)
                        failed += 1
                    else:
                        chunks = result.get('num_chunks', 0)
                        new_chunks = result.get('new_chunks_embedded', 0)
                        self.console.print(f"✅ Ingested {os.path.basename(file_path)}: {chunks} chunks, {new_chunks} new", 
                                         style=Colors.SUCCESS)
                        successful += 1
                        
                except Exception as e:
                    self.console.print(f"❌ Error processing {os.path.basename(file_path)}: {e}", 
                                     style=Colors.ERROR)
                    failed += 1
                
                # Update progress
                progress.update(main_task, advance=1)
        
        # Summary
        self.console.print(f"\n📊 Ingestion complete: {successful} successful, {failed} failed", 
                         style=Colors.SUCCESS if failed == 0 else Colors.WARNING)
        
    def handle_remove_command(self, command: str):
        """Handle document removal command."""
        # Parse command arguments
        parts = command.split()
        if len(parts) < 2:
            self.console.print("❌ Usage: /remove <file_path> [file_path2 ...] or /rm <file_path>", 
                             style=Colors.ERROR)
            self.console.print("Examples:", style=Colors.TEXT_MUTED)
            self.console.print("  /remove document.pdf", style=Colors.TEXT_MUTED)
            self.console.print("  /remove *.txt", style=Colors.TEXT_MUTED)
            self.console.print("  /remove folder/", style=Colors.TEXT_MUTED)
            self.console.print("  /remove file1.pdf file2.txt", style=Colors.TEXT_MUTED)
            return
        
        # Show immediate progress for setup work
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            setup_task = progress.add_task("[cyan]Preparing files for removal...", total=None)
            
            # Get file paths/patterns from command
            file_patterns = parts[1:]
            
            # Expand glob patterns and resolve paths
            expanded_paths = []
            for pattern in file_patterns:
                # Expand glob patterns
                matches = glob.glob(pattern)
                if matches:
                    expanded_paths.extend(matches)
                else:
                    # If no glob matches, try common locations and treat as literal
                    possible_paths = [
                        pattern,  # As given
                        f"data/documents/{pattern}",  # In documents directory
                        f"./{pattern}",  # Explicit relative
                    ]
                    
                    # For removal, we don't need the file to exist on disk
                    # We just collect all possible patterns to search in DB
                    expanded_paths.append(pattern)
                    
                    # Also try with data/documents prefix for better matching
                    if not pattern.startswith('data/documents/'):
                        expanded_paths.append(f"data/documents/{pattern}")
            
            # Remove duplicates
            expanded_paths = list(set(expanded_paths))
            
            if not expanded_paths:
                progress.update(setup_task, visible=False)
                self.console.print("❌ No file patterns specified for removal", 
                                 style=Colors.ERROR)
                return
                
            # Mark setup complete
            progress.update(setup_task, completed=True, visible=False)
        
        self.console.print(f"🔍 Searching for {len(expanded_paths)} pattern(s) to remove", 
                         style=Colors.INFO)
        
        # Find and remove files
        removed_files = 0
        removed_chunks = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("({task.completed}/{task.total})"),
            console=self.console
        ) as progress:
            main_task = progress.add_task(f"[cyan]Processing {len(expanded_paths)} pattern(s)...", total=len(expanded_paths))
            
            for i, pattern in enumerate(expanded_paths):
                # Update progress description for current pattern
                progress.update(main_task, description=f"[cyan]Searching for {os.path.basename(pattern)}...")
                
                try:
                    # Search the database for files matching this pattern
                    import sqlite3
                    from samvaad.utils.filehash_db import DB_PATH, delete_file_and_cleanup
                    from samvaad.pipeline.vectorstore.vectorstore import get_collection
                    
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    
                    # Create search patterns for different matching strategies
                    basename = os.path.basename(pattern)
                    dirname = os.path.dirname(pattern) if os.path.dirname(pattern) else ""
                    
                    # Search queries - try multiple matching strategies
                    search_queries = []
                    
                    # 1. Exact filename match
                    search_queries.append(('SELECT file_id, filename FROM file_metadata WHERE filename = ?', (pattern,)))
                    
                    # 2. Basename match (for files that might have been stored with different paths)
                    if basename != pattern:
                        search_queries.append(('SELECT file_id, filename FROM file_metadata WHERE filename LIKE ?', (f'%{basename}%',)))
                    
                    # 3. Full pattern match with wildcards
                    if '*' in pattern or '?' in pattern:
                        # Convert glob to SQL LIKE pattern
                        sql_pattern = pattern.replace('*', '%').replace('?', '_')
                        search_queries.append(('SELECT file_id, filename FROM file_metadata WHERE filename LIKE ?', (sql_pattern,)))
                    
                    # 4. Directory match - find all files in directory
                    if dirname and not basename:
                        search_queries.append(('SELECT file_id, filename FROM file_metadata WHERE filename LIKE ?', (f'{dirname}/%',)))
                    
                    # Collect all matching files
                    all_matches = set()
                    for query, params in search_queries:
                        c.execute(query, params)
                        matches = c.fetchall()
                        all_matches.update(matches)
                    
                    conn.close()
                    
                    if not all_matches:
                        self.console.print(f"⚠️  No ingested files found matching: {pattern}", 
                                         style=Colors.WARNING)
                        progress.update(main_task, advance=1)
                        continue
                    
                    # Remove each matching file
                    pattern_removed = 0
                    pattern_chunks = 0
                    
                    for file_id, stored_filename in all_matches:
                        self.console.print(f"🗑️  Removing {stored_filename}...", 
                                         style=Colors.INFO)
                        
                        # Get orphaned chunks and remove from DB
                        orphaned_chunks = delete_file_and_cleanup(file_id)
                        
                        # Remove orphaned chunks from ChromaDB
                        if orphaned_chunks:
                            try:
                                collection = get_collection()
                                collection.delete(ids=orphaned_chunks)
                                pattern_chunks += len(orphaned_chunks)
                            except Exception as e:
                                self.console.print(f"⚠️  Warning: Could not remove some chunks from vector store: {e}", 
                                                 style=Colors.WARNING)
                        
                        pattern_removed += 1
                        removed_files += 1
                        removed_chunks += pattern_chunks
                        
                        self.console.print(f"✅ Removed {stored_filename}: {len(orphaned_chunks)} chunks deleted", 
                                         style=Colors.SUCCESS)
                    
                    if pattern_removed > 0:
                        self.console.print(f"📊 Pattern '{pattern}': {pattern_removed} files removed", 
                                         style=Colors.SUCCESS)
                        
                except Exception as e:
                    self.console.print(f"❌ Error processing pattern {pattern}: {e}", 
                                     style=Colors.ERROR)
                
                # Update progress
                progress.update(main_task, advance=1)
        
        # Summary
        if removed_files > 0:
            self.console.print(f"\n📊 Bulk removal complete: {removed_files} files removed, {removed_chunks} chunks deleted", 
                             style=Colors.SUCCESS)
        else:
            self.console.print("\n📊 No files were removed", 
                             style=Colors.INFO)
        
    def start_voice_mode(self):
        """Start voice conversation mode with immediate progress feedback."""
        self.console.print("Starting voice mode...", 
                         style=Colors.VOICE_ACTIVE)
        
        # Use a progress bar to cover the entire initialization, including heavy imports
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            # Task for initial setup (imports and component init)
            init_task = progress.add_task("[cyan]Initializing voice components...", total=None)
            
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
                
                try:
                    # Define loading steps
                    whisper_task = progress.add_task("[cyan]Loading Whisper model...", total=None)
                    embedding_task = progress.add_task("[cyan]Loading embedding model...", total=None)
                    tts_task = progress.add_task("[cyan]Loading Kokoro TTS...", total=None)
                    
                    # Preload models one by one
                    try:
                        from samvaad.pipeline.retrieval.voice_mode import initialize_whisper_model
                        initialize_whisper_model(model_size="small", device="auto")
                        progress.update(whisper_task, completed=True, visible=False)
                    except Exception as e:
                        progress.update(whisper_task, description=f"[red]Failed to load Whisper: {e}", completed=True)
                    
                    try:
                        from samvaad.pipeline.retrieval.query import get_embedding_model
                        get_embedding_model()
                        progress.update(embedding_task, completed=True, visible=False)
                    except Exception as e:
                        progress.update(embedding_task, description=f"[red]Failed to load embedding model: {e}", completed=True)
                    
                    try:
                        from samvaad.pipeline.retrieval.voice_mode import get_kokoro_tts
                        get_kokoro_tts()
                        progress.update(tts_task, completed=True, visible=False)
                    except Exception as e:
                        progress.update(tts_task, description=f"[red]Failed to load TTS: {e}", completed=True)
                        
                finally:
                    # Always restore stdout
                    sys.stdout = old_stdout

            except (ImportError, RuntimeError) as e:
                # If any part of initialization fails, hide progress and show error
                progress.update(init_task, visible=False)
                self.console.print(f"❌ Voice mode unavailable: {e}", 
                                 style=Colors.ERROR)
                self.console.print("Install voice dependencies: uv pip install sounddevice webrtcvad faster-whisper", 
                                 style=Colors.TEXT_MUTED)
                return

        # All loading is done, now start voice conversation
        self.run_voice_conversation()
            
    def run_voice_conversation(self):
        """Run the continuous voice conversation mode."""
        try:
            # Import the voice mode from voice_mode module
            from samvaad.pipeline.retrieval.voice_mode import VoiceMode
            
            # Create progress callbacks for voice mode stages
            def listening_callback():
                return Progress(
                    SpinnerColumn(),
                    TextColumn("[cyan]{task.description}"),
                    console=self.console,
                    transient=True
                )
            
            def transcribing_callback():
                return Progress(
                    SpinnerColumn(),
                    TextColumn("[cyan]{task.description}"),
                    console=self.console,
                    transient=True
                )
            
            def processing_callback():
                return Progress(
                    SpinnerColumn(),
                    TextColumn("[cyan]{task.description}"),
                    console=self.console,
                    transient=True
                )
            
            def speaking_callback():
                return Progress(
                    SpinnerColumn(),
                    TextColumn("[cyan]{task.description}"),
                    console=self.console,
                    transient=True
                )
            
            def response_callback(response_text: str, query_time: float = None):
                """Format voice response using the same UI as text responses."""
                self.format_ai_response(response_text, query_time=query_time)
            
            progress_callbacks = {
                'listening': listening_callback,
                'transcribing': transcribing_callback,
                'processing': processing_callback,
                'speaking': speaking_callback,
                'response': response_callback
            }
            
            # Create and run voice mode with progress callbacks
            voice_mode = VoiceMode(progress_callbacks=progress_callbacks)
            voice_mode.run()
            
            # After voice mode completes, show option to continue or return to text mode
            self.console.print("\n" + "="*50, style=Colors.TEXT_MUTED)
            self.console.print("Voice conversation completed!", style=Colors.SUCCESS)
            self.console.print("Returning to text mode...", style=Colors.INFO)
            self.console.print("Use /voice again for another voice session.", style=Colors.TEXT_SECONDARY)
            
        except KeyboardInterrupt:
            self.console.print("\n📝 Returning to text mode...", 
                             style=Colors.INFO)
        except Exception as e:
            self.console.print(f"❌ Voice mode error: {e}", 
                             style=Colors.ERROR)
            
    def init_conversation_components(self):
        """Initialize conversation manager and loop."""
        try:
            # Import conversation components
            from samvaad.pipeline.retrieval.voice_mode import ConversationManager
            
            # Initialize conversation manager if not already done
            if not self.conversation_manager:
                self.conversation_manager = ConversationManager(
                    max_history=50,
                    context_window=10
                )
            
        except Exception as e:
            self.console.print(f"❌ Failed to initialize conversation components: {e}", 
                             style=Colors.ERROR)
            
    def process_text_query(self, query: str):
        """Process a text query through the RAG pipeline."""
        query_start_time = time.time()
        
        # Show immediate progress for setup work
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            setup_task = progress.add_task("[cyan]Preparing query processing...", total=None)
            
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
                self.console.print(f"❌ Error initializing query processing: {e}", 
                                 style=Colors.ERROR)
                return {
                    'answer': f"Sorry, I encountered an error: {e}",
                    'success': False,
                    'sources': []
                }
        
        # Enhanced query processing with detailed steps
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            # Multi-step progress tracking
            search_task = progress.add_task("[cyan]Searching documents...", total=None)
            
            try:
                # Process the query
                result = rag_query_pipeline(
                    query,
                    model="gemini-2.5-flash",
                    conversation_manager=self.conversation_manager
                )
                
                # Update to generation phase
                progress.update(search_task, description="[cyan]Generating response...")
                
                # Small delay to show the generation message
                time.sleep(0.1)
                
                # Mark as complete
                progress.update(search_task, completed=True, visible=False)
                
                # Calculate total time
                query_time = time.time() - query_start_time
                result['query_time'] = query_time
                
                # Update stats
                self.session_stats['messages'] += 1
                self.session_stats['text_queries'] += 1
                
                return result
                
            except Exception as e:
                # Hide progress on error
                progress.update(search_task, visible=False)
                
                self.console.print(f"❌ Error processing query: {e}", 
                                 style=Colors.ERROR)
                return {
                    'answer': f"Sorry, I encountered an error: {e}",
                    'success': False,
                    'sources': [],
                    'query_time': time.time() - query_start_time
                }
                
    def run_interactive_loop(self):
        """Main interactive loop for text-based conversation."""
        try:
            while not self._should_exit:
                try:
                    # Get user input with rich prompt
                    user_input = self.prompt_session.prompt(
                        HTML('<ansicyan>❯ </ansicyan>'),
                        multiline=False
                    )
                    
                    # Handle None or empty input
                    if user_input  is None or self._should_exit:
                        break
                    
                    user_input = user_input.strip()
                    if not user_input:
                        continue
                        
                    # Handle slash commands
                    if user_input.startswith('/'):
                        if not self.handle_slash_command(user_input):
                            break
                        continue
                        
                    # Process query and get response
                    result = self.process_text_query(user_input)
                    
                    # Display AI response with enhanced formatting
                    if result and result.get('answer'):
                        self.format_ai_response(
                            result['answer'], 
                            result.get('sources', []),
                            result.get('query_time')
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
        self.session_stats['start_time'] = time.time()
        
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
    @click.option('--voice', '-v', is_flag=True, help='Start directly in voice mode')
    @click.option('--help-cmd', '--help', is_flag=True, help='Show help and exit')
    @click.version_option(version='0.1.0', prog_name='Samvaad')
    def cli(voice, help_cmd):
        """
        🎙️ Samvaad - AI Conversational Assistant
        
        An intelligent assistant that understands voice and text, with document awareness
        and contextual conversations powered by advanced AI models.
        
        Examples:
        
        \b
        samvaad                 # Start interactive mode
        samvaad --voice         # Start in voice mode
        samvaad --help          # Show this help
        """
        if help_cmd:
            ctx = click.get_current_context()
            click.echo(ctx.get_help())
            return
            
        try:
            # Initialize and start the interface
            interface = SamvaadInterface()
            
            if voice:
                # Start directly in voice mode
                console.clear()
                interface.display_banner()
                interface.start_voice_mode()
            else:
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