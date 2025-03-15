# services/sync/src/main.py
import os
import json
import time
import logging
import mysql.connector
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from kafka import KafkaConsumer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sync")

# Configuration from environment variables
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC_INPUT = os.getenv("KAFKA_TOPIC_INPUT", "processed-transcripts")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "sync-group")

MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "password")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "transcription_db")

ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
ELASTICSEARCH_PORT = os.getenv("ELASTICSEARCH_PORT", "9200")
ELASTICSEARCH_USER = os.getenv("ELASTICSEARCH_USER", "elastic")
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "changeme")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "transcriptions")

FULL_SYNC_INTERVAL = int(os.getenv("FULL_SYNC_INTERVAL", "3600"))  # seconds (1 hour)

# Initialize Kafka consumer
consumer = KafkaConsumer(
    KAFKA_TOPIC_INPUT,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id=KAFKA_GROUP_ID,
    auto_offset_reset='earliest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

def get_mysql_connection():
    """Establish connection to MySQL"""
    return mysql.connector.connect(
        host=MYSQL_HOST,
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

def ensure_index_exists(es):
    """Ensure Elasticsearch index exists with proper mappings"""
    try:
        if not es.indices.exists(index=ELASTICSEARCH_INDEX):
            es.indices.create(
                index=ELASTICSEARCH_INDEX,
                body={
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0
                    },
                    "mappings": {
                        "properties": {
                            "audio_id": {"type": "keyword"},
                            "transcript": {
                                "type": "text",
                                "analyzer": "standard",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                }
                            },
                            "is_valid": {"type": "boolean"},
                            "update_date": {"type": "date"},
                            "creation_date": {"type": "date"},
                            "input_source": {"type": "keyword"},
                            "audio_url": {"type": "keyword"}
                        }
                    }
                }
            )
            logger.info(f"Created Elasticsearch index: {ELASTICSEARCH_INDEX}")
        return True
    except Exception as e:
        logger.error(f"Error creating Elasticsearch index: {e}")
        return False

def upsert_to_elasticsearch(es, data):
    """Insert or update document in Elasticsearch"""
    try:
        # Format dates correctly for Elasticsearch
        for date_field in ['update_date', 'creation_date']:
            if data.get(date_field):
                # Try to parse various date formats
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field]).isoformat()
                except:
                    try:
                        data[date_field] = datetime.strptime(data[date_field], '%Y-%m-%d %H:%M:%S').isoformat()
                    except:
                        logger.warning(f"Could not parse date: {data[date_field]}")
        
        es.index(
            index=ELASTICSEARCH_INDEX,
            id=data['audio_id'],
            document=data
        )
        logger.info(f"Upserted document to Elasticsearch: {data['audio_id']}")
        return True
    except Exception as e:
        logger.error(f"Error upserting to Elasticsearch: {e}")
        return False

def process_kafka_message(es, data):
    """Process incoming Kafka message"""
    try:
        return upsert_to_elasticsearch(es, data)
    except Exception as e:
        logger.error(f"Error processing Kafka message: {e}")
        return False

def fetch_all_from_mysql(last_sync_time=None):
    """Fetch all records from MySQL, optionally filtered by update time"""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT audio_id, transcript, is_valid, update_date, creation_date, input_source
            FROM transcriptions
        """
        
        params = []
        if last_sync_time:
            query += " WHERE update_date > %s"
            params.append(last_sync_time)
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        # Convert MySQL datetime objects to ISO format strings
        for record in records:
            record['update_date'] = record['update_date'].isoformat() if record['update_date'] else None
            record['creation_date'] = record['creation_date'].isoformat() if record['creation_date'] else None
        logger.info(f"Fetched {len(records)} records from MySQL")
        
        cursor.close()
        conn.close()
        
        return records
    except Exception as e:
        logger.error(f"Error fetching from MySQL: {e}")
        return []

def perform_full_sync(es):
    """Perform a full sync from MySQL to Elasticsearch"""
    try:
        logger.info("Starting full sync")
        
        # Get all records from MySQL
        records = fetch_all_from_mysql()
        
        # Batch insert/update into Elasticsearch
        success_count = 0
        for record in records:
            if upsert_to_elasticsearch(es, record):
                success_count += 1
        
        logger.info(f"Full sync completed. Successfully synced {success_count}/{len(records)} records")
        return success_count
    except Exception as e:
        logger.error(f"Error during full sync: {e}")
        return 0

def main():
    """Main sync service loop"""
    logger.info("Starting sync service")
    
    # Initialize Elasticsearch client
    es = get_elasticsearch_client()
    
    # Ensure index exists
    if not ensure_index_exists(es):
        logger.error("Failed to create Elasticsearch index. Exiting.")
        return
    
    # Perform initial full sync
    perform_full_sync(es)
    last_full_sync = datetime.now()
    
    # Start processing Kafka messages for real-time updates
    try:
        for message in consumer:
            try:
                data = message.value
                process_kafka_message(es, data)
                
                # Check if it's time for a full sync
                if (datetime.now() - last_full_sync).total_seconds() > FULL_SYNC_INTERVAL:
                    perform_full_sync(es)
                    last_full_sync = datetime.now()
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    except KeyboardInterrupt:
        logger.info("Sync service shutting down")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    # Allow time for services to start
    time.sleep(20)
    main()