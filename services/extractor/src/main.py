# services/extractor/src/main.py
import os
import time
import json
import logging
import requests
import mysql.connector
from kafka import KafkaProducer
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("extractor")

# Configuration from environment variables
YOUTUBE_DB_HOST = os.getenv("YOUTUBE_DB_HOST", "youtube-db")
YOUTUBE_DB_USER = os.getenv("YOUTUBE_DB_USER", "root")
YOUTUBE_DB_PASSWORD = os.getenv("YOUTUBE_DB_PASSWORD", "password")
YOUTUBE_DB_NAME = os.getenv("YOUTUBE_DB_NAME", "youtube_db")

API_ENDPOINT = os.getenv("API_ENDPOINT", "http://mock-api:8080/transcripts")
API_POLLING_INTERVAL = int(os.getenv("API_POLLING_INTERVAL", "60"))  # seconds

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_OUTPUT", "raw-transcripts")

# Create Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def get_youtube_connection():
    """Establish connection to YouTube DB"""
    return mysql.connector.connect(
        host=YOUTUBE_DB_HOST,
        user=YOUTUBE_DB_USER,
        password=YOUTUBE_DB_PASSWORD,
        database=YOUTUBE_DB_NAME
    )

def extract_from_youtube_db(last_update=None):
    """Extract new or updated records from YouTube DB"""
    try:
        conn = get_youtube_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                video_url, channel, start_time, end_time, 
                transcript, is_valid, update_date, creation_date
            FROM transcripts
            WHERE 1=1
        """
        
        params = []
        if last_update:
            query += " AND update_date > %s"
            params.append(last_update)
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        logger.info(f"Extracted {len(records)} records from YouTube DB")
        
        # Convert MySQL datetime objects to ISO format strings
        for record in records:
            record['update_date'] = record['update_date'].isoformat()
            record['creation_date'] = record['creation_date'].isoformat()
            record['source'] = 'youtube'
        
        cursor.close()
        conn.close()
        
        return records
    except Exception as e:
        logger.error(f"Error extracting from YouTube DB: {e}")
        return []

def extract_from_api():
    """Extract data from Custom API"""
    try:
        response = requests.get(API_ENDPOINT)
        if response.status_code == 200:
            records = response.json()
            logger.info(f"Extracted {len(records)} records from Custom API")
            
            # Add source information
            for record in records:
                record['source'] = 'custom'
            
            return records
        else:
            logger.error(f"API returned status code {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error extracting from API: {e}")
        return []

def send_to_kafka(records, source):
    """Send extracted records to Kafka"""
    for record in records:
        try:
            # Add metadata about source
            record['input_source'] = source
            record['extraction_time'] = datetime.now().isoformat()
            
            # Send to Kafka
            producer.send(KAFKA_TOPIC, record)
            logger.debug(f"Sent record to Kafka: {record.get('video_url', 'custom')}")
        except Exception as e:
            logger.error(f"Error sending record to Kafka: {e}")
    
    producer.flush()

def main():
    """Main extraction loop"""
    youtube_last_update = None
    
    logger.info("Starting extraction service")
    
    while True:
        try:
            # Extract from YouTube DB
            youtube_records = extract_from_youtube_db(youtube_last_update)
            if youtube_records:
                send_to_kafka(youtube_records, 'youtube')
                # Update last processed timestamp
                youtube_last_update = max(r['update_date'] for r in youtube_records)
            
            # Extract from Custom API
            api_records = extract_from_api()
            if api_records:
                send_to_kafka(api_records, 'custom')
            
            logger.info(f"Completed extraction cycle. Waiting {API_POLLING_INTERVAL} seconds...")
            time.sleep(API_POLLING_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in extraction cycle: {e}")
            time.sleep(10)  # Wait a bit before retrying

if __name__ == "__main__":
    # Allow time for Kafka to start
    time.sleep(10)
    main()