"""Tests for clean_markdown utility."""

from samvaad.utils.clean_markdown import strip_markdown


class TestStripMarkdown:
    """Test markdown stripping functionality."""

    def test_strip_markdown_basic(self):
        """Test basic markdown removal."""
        text = "**Bold** and *Italic* text."
        expected = "Bold and Italic text."
        assert strip_markdown(text) == expected

    def test_strip_markdown_headers(self):
        """Test header removal."""
        text = "# Header 1\n## Header 2\nContent"
        expected = "Header 1\nHeader 2\nContent"
        assert strip_markdown(text) == expected

    def test_strip_markdown_links_images(self):
        """Test link and image removal."""
        text = "Check [this link](http://example.com) and ![image](img.png)."
        expected = "Check this link and image."
        assert strip_markdown(text) == expected

    def test_strip_markdown_code_blocks(self):
        """Test code block removal."""
        text = "Code:\n```python\nprint('hello')\n```\nEnd."
        expected = "Code:\n\nEnd."
        assert strip_markdown(text) == expected

    def test_strip_markdown_inline_code(self):
        """Test inline code removal."""
        text = "Use `print()` function."
        expected = "Use print() function."
        assert strip_markdown(text) == expected

    def test_strip_markdown_lists(self):
        """Test list formatting removal."""
        text = "- Item 1\n* Item 2\n+ Item 3"
        expected = "Item 1\nItem 2\nItem 3"
        assert strip_markdown(text) == expected

    def test_strip_markdown_empty_none(self):
        """Test empty or None input."""
        assert strip_markdown("") == ""
        assert strip_markdown(None) is None
