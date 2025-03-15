# tests/component/test_transformer.py
import os
import json
import pytest
from unittest.mock import patch, MagicMock
import sys
import io

# Add the service path to import the module
sys.path.append(os.path.join(os.path.dirname(__file__), '../../services/transformer/src'))

# Mock environment variables
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "mock:9092")
    monkeypatch.setenv("KAFKA_TOPIC_INPUT", "raw-transcripts")
    monkeypatch.setenv("KAFKA_TOPIC_OUTPUT", "processed-transcripts")
    monkeypatch.setenv("MYSQL_HOST", "mock-mysql")
    monkeypatch.setenv("MYSQL_USER", "root")
    monkeypatch.setenv("MYSQL_PASSWORD", "password")
    monkeypatch.setenv("MINIO_ENDPOINT", "mock:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minio")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minio123")

# Mock the imports
@pytest.fixture(autouse=True)
def mock_imports():
    modules_to_mock = [
        'mysql.connector',
        'kafka.KafkaConsumer',
        'kafka.KafkaProducer',
        'boto3'
    ]
    
    mocks = {}
    for module in modules_to_mock:
        patcher = patch(module)
        mocks[module] = patcher.start()
        yield
        patcher.stop()

class TestTransformerService:
    @patch('main.store_audio_file')
    @patch('main.save_to_mysql')
    def test_transform_youtube_data(self, mock_save_mysql, mock_store_audio):
        """Test transforming YouTube data"""
        # Import the main module (after mocking dependencies)
        import main
        
        # Create a sample YouTube record
        youtube_data = {
            'video_url': 'https://youtube.com/watch?v=abc123',
            'transcript': 'This is a test transcript',
            'is_valid': True,
            'update_date': '2023-01-01T12:00:00',
            'creation_date': '2023-01-01T10:00:00',
            'input_source': 'youtube'
        }
        
        # Transform the data
        transformed = main.transform_youtube_data(youtube_data)
        
        # Verify the result
        assert transformed['transcript'] == 'This is a test transcript'
        assert transformed['is_valid'] == True
        assert transformed['input_source'] == 'youtube'
        assert transformed['audio_id'].startswith('yt-')
        assert 'update_date' in transformed
        assert 'creation_date' in transformed
    
    @patch('main.store_audio_file')
    @patch('main.save_to_mysql')
    def test_transform_custom_api_data(self, mock_save_mysql, mock_store_audio):
        """Test transforming Custom API data"""
        # Import the main module (after mocking dependencies)
        import main
        
        # Set up the mock for storing audio files
        mock_store_audio.return_value = 's3://audio-files/test-audio-id.wav'
        
        # Create a sample Custom API record
        custom_data = {
            'audio_bytes': b'fake_audio_bytes',
            'transcript': 'Custom API transcript test',
            'is_valid': True,
            'update_date': '2023-01-02T12:00:00',
            'creation_date': '2023-01-02T10:00:00',
            'input_source': 'custom'
        }
        
        # Transform the data
        transformed = main.transform_custom_api_data(custom_data)
        
        # Verify the result
        assert transformed['transcript'] == 'Custom API transcript test'
        assert transformed['is_valid'] == True
        assert transformed['input_source'] == 'custom'
        assert transformed['audio_id'].startswith('custom-')
        assert transformed['audio_url'] == 's3://audio-files/test-audio-id.wav'
        assert 'update_date' in transformed
        assert 'creation_date' in transformed
        
        # Verify store_audio_file was called
        mock_store_audio.assert_called_once()

# tests/component/test_sync.py
import os
import json
import pytest
from unittest.mock import patch, MagicMock
import sys

# Add the service path to import the module
sys.path.append(os.path.join(os.path.dirname(__file__), '../../services/sync/src'))

# Mock environment variables
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "mock:9092")
    monkeypatch.setenv("KAFKA_TOPIC_INPUT", "processed-transcripts")
    monkeypatch.setenv("MYSQL_HOST", "mock-mysql")
    monkeypatch.setenv("MYSQL_USER", "root")
    monkeypatch.setenv("MYSQL_PASSWORD", "password")
    monkeypatch.setenv("ELASTICSEARCH_HOST", "mock-es")
    monkeypatch.setenv("ELASTICSEARCH_PORT", "9200")
    monkeypatch.setenv("ELASTICSEARCH_USER", "elastic")
    monkeypatch.setenv("ELASTICSEARCH_PASSWORD", "changeme")

# Mock the imports
@pytest.fixture(autouse=True)
def mock_imports():
    modules_to_mock = [
        'mysql.connector',
        'kafka.KafkaConsumer',
        'elasticsearch.Elasticsearch'
    ]
    
    mocks = {}
    for module in modules_to_mock:
        patcher = patch(module)
        mocks[module] = patcher.start()
        yield
        patcher.stop()

class TestSyncService:
    @patch('main.get_elasticsearch_client')
    def test_ensure_index_exists(self, mock_es_client):
        """Test ensuring Elasticsearch index exists"""
        # Import the main module (after mocking dependencies)
        import main
        
        # Set up mock ES client
        es_mock = MagicMock()
        es_mock.indices.exists.return_value = False
        mock_es_client.return_value = es_mock
        
        # Call the function
        result = main.ensure_index_exists(es_mock)
        
        # Verify the result
        assert result == True
        es_mock.indices.create.assert_called_once()
    
    @patch('main.get_elasticsearch_client')
    def test_upsert_to_elasticsearch(self, mock_es_client):
        """Test upserting document to Elasticsearch"""
        # Import the main module (after mocking dependencies)
        import main
        
        # Set up mock ES client
        es_mock = MagicMock()
        mock_es_client.return_value = es_mock
        
        # Sample data
        data = {
            'audio_id': 'test-123',
            'transcript': 'Test transcript',
            'is_valid': True,
            'update_date': '2023-01-01T12:00:00',
            'creation_date': '2023-01-01T10:00:00',
            'input_source': 'youtube'
        }
        
        # Call the function
        result = main.upsert_to_elasticsearch(es_mock, data)
        
        # Verify the result
        assert result == True
        es_mock.index.assert_called_once_with(
            index=main.ELASTICSEARCH_INDEX,
            id='test-123',
            document=data
        )