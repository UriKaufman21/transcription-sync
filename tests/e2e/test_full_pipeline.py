# tests/e2e/test_full_pipeline.py
import os
import json
import time
import pytest
import requests
import mysql.connector
from elasticsearch import Elasticsearch

# Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_ROOT_PASSWORD", "password")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "transcription_db")

ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "localhost")
ELASTICSEARCH_PORT = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
ELASTICSEARCH_USER = os.getenv("ELASTICSEARCH_USER", "elastic")
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "changeme")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "transcriptions")

MOCK_API_URL = os.getenv("MOCK_API_URL", "http://localhost:8080/transcripts")

def get_mysql_connection():
    """Establish connection to MySQL"""
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

def get_elasticsearch_client():
    """Establish connection to Elasticsearch"""
    return Elasticsearch(
        f"http://{ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}",
        basic_auth=(ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORD),
        verify_certs=False
    )

class TestE2EPipeline:
    @pytest.fixture(scope="class")
    def setup(self):
        """Wait for services to be ready"""
        # Give the system time to initialize
        time.sleep(20)
        yield
    
    def test_mock_api_available(self, setup):
        """Test that the mock API is available"""
        response = requests.get(MOCK_API_URL)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_mysql_connection(self, setup):
        """Test connection to MySQL"""
        conn = get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        cursor.close()
        conn.close()
        
        table_names = [t[0] for t in tables]
        assert "transcriptions" in table_names
    
    def test_elasticsearch_connection(self, setup):
        """Test connection to Elasticsearch"""
        es = get_elasticsearch_client()
        info = es.info()
        assert info['cluster_name'] is not None
    
    def test_elasticsearch_index_exists(self, setup):
        """Test that the Elasticsearch index exists"""
        es = get_elasticsearch_client()
        assert es.indices.exists(index=ELASTICSEARCH_INDEX)
    
    def test_data_flow_completion(self, setup):
        """Test complete data flow through the system"""
        # Wait for the pipeline to process data
        time.sleep(60)
        
        # Check MySQL for processed data
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as count FROM transcriptions")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # We should have data in MySQL
        assert result['count'] > 0
        
        # Check Elasticsearch for synced data
        es = get_elasticsearch_client()
        result = es.count(index=ELASTICSEARCH_INDEX)
        
        # We should have data in Elasticsearch
        assert result['count'] > 0
    
    def test_data_consistency(self, setup):
        """Test data consistency between MySQL and Elasticsearch"""
        # Get a sample record from MySQL
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM transcriptions LIMIT 1")
        mysql_record = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not mysql_record:
            pytest.skip("No data in MySQL to check consistency")
        
        # Check if the same record exists in Elasticsearch
        es = get_elasticsearch_client()
        try:
            es_record = es.get(index=ELASTICSEARCH_INDEX, id=mysql_record['audio_id'])
            assert es_record['found']
            assert es_record['_source']['transcript'] == mysql_record['transcript']
            assert es_record['_source']['input_source'] == mysql_record['input_source']
        except Exception as e:
            pytest.fail(f"Failed to verify data consistency: {e}")