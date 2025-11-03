"""Shared pytest fixtures for Samvaad tests."""

import os
import sys
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add tests/utils to path
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for database files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_audio_dir():
    """Create a temporary directory for audio files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_text():
    """Provide sample text for testing."""
    return "This is a sample text for testing purposes. It contains multiple sentences."


@pytest.fixture
def sample_texts():
    """Provide multiple sample texts for batch testing."""
    return [
        "First sample text for testing.",
        "Second sample text with different content.",
        "Third sample text to verify batch processing."
    ]


@pytest.fixture
def sample_document():
    """Provide a sample document for testing."""
    return """# Sample Document

This is a sample document for testing the RAG pipeline.

## Section 1

Here is some content in section 1. It talks about various topics related to testing.

## Section 2

More content in section 2. This section discusses different aspects of the system.
"""


@pytest.fixture
def mock_gemini_api():
    """Mock Gemini API for testing."""
    with patch('google.genai.Client') as mock_client:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is a test response from Gemini."
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ['GEMINI_API_KEY'] = 'test_api_key'
    os.environ['HF_TOKEN'] = 'test_hf_token'
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_sounddevice():
    """Mock sounddevice module for audio testing."""
    from tests.utils.mock_audio import create_mock_sounddevice
    
    mock_sd, mock_stream = create_mock_sounddevice()
    
    with patch.dict('sys.modules', {'sounddevice': mock_sd}):
        yield mock_sd, mock_stream


@pytest.fixture
def mock_webrtcvad():
    """Mock webrtcvad module for VAD testing."""
    from tests.utils.mock_audio import create_mock_webrtcvad
    
    mock_vad_module, mock_vad_instance = create_mock_webrtcvad()
    
    with patch.dict('sys.modules', {'webrtcvad': mock_vad_module}):
        yield mock_vad_module, mock_vad_instance


@pytest.fixture
def mock_whisper_model():
    """Mock Whisper model for transcription testing."""
    mock_model = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = "This is a transcribed text."
    mock_model.transcribe.return_value = ([mock_segment], None)
    return mock_model


@pytest.fixture
def mock_tts_engine():
    """Mock TTS engine for audio generation testing."""
    from tests.utils.mock_audio import generate_fake_audio_data
    
    mock_engine = MagicMock()
    pcm_data = generate_fake_audio_data(duration_seconds=1.0)
    mock_engine.synthesize.return_value = (pcm_data, 16000, 2, 1)
    mock_engine.available_languages.return_value = ['en', 'es', 'fr']
    return mock_engine


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment before each test."""
    # Suppress warnings during tests
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    yield
    
    # Cleanup if needed


@pytest.fixture
def sample_chunks():
    """Provide sample chunks for testing."""
    return [
        {
            'chunk_id': 'chunk_1',
            'file_id': 'file_1',
            'text': 'First chunk of text for testing retrieval.',
            'metadata': {'source': 'test_doc.txt', 'page': 1}
        },
        {
            'chunk_id': 'chunk_2',
            'file_id': 'file_1',
            'text': 'Second chunk with different content about AI.',
            'metadata': {'source': 'test_doc.txt', 'page': 1}
        },
        {
            'chunk_id': 'chunk_3',
            'file_id': 'file_2',
            'text': 'Third chunk from a different document.',
            'metadata': {'source': 'test_doc2.txt', 'page': 1}
        }
    ]
