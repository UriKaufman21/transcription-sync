# services/transformer/src/main.py
import os
import io
import json
import uuid
import time
import base64
import logging
import mysql.connector
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime
import boto3
from botocore.client import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("transformer")

# Configuration from environment variables
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC_INPUT = os.getenv("KAFKA_TOPIC_INPUT", "raw-transcripts")
KAFKA_TOPIC_OUTPUT = os.getenv("KAFKA_TOPIC_OUTPUT", "processed-transcripts")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "transformer-group")

MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "password")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "transcription_db")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "audio-files")

# Initialize Kafka consumer
consumer = KafkaConsumer(
    KAFKA_TOPIC_INPUT,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id=KAFKA_GROUP_ID,
    auto_offset_reset='earliest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Initialize Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Initialize MinIO client
s3_client = boto3.client(
    's3',
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

def get_mysql_connection():
    """Establish connection to MySQL"""
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

def ensure_bucket_exists():
    """Ensure the MinIO bucket exists"""
    try:
        s3_client.head_bucket(Bucket=MINIO_BUCKET_NAME)
    except:
        s3_client.create_bucket(Bucket=MINIO_BUCKET_NAME)
        logger.info(f"Created bucket: {MINIO_BUCKET_NAME}")

def store_audio_file(audio_data, audio_id):
    """Store audio file in MinIO and return the URL"""
    try:
        # For YouTube data, we might need to download the audio separately
        # Here we assume audio_data is provided directly (e.g. from the custom API)
        if audio_data:
            # Handle base64 encoded audio
            if isinstance(audio_data, str) and audio_data.startswith('data:audio'):
                # Extract the base64 part
                audio_data = audio_data.split(',')[1]
                audio_bytes = base64.b64decode(audio_data)
            elif isinstance(audio_data, bytes):
                audio_bytes = audio_data
            else:
                audio_bytes = audio_data.encode('utf-8')
                
            # Upload to MinIO
            s3_client.put_object(
                Bucket=MINIO_BUCKET_NAME,
                Key=f"{audio_id}.wav",
                Body=io.BytesIO(audio_bytes),
                ContentType='audio/wav'
            )
            
            logger.info(f"Stored audio file with ID: {audio_id}")
            return f"s3://{MINIO_BUCKET_NAME}/{audio_id}.wav"
        return None
    except Exception as e:
        logger.error(f"Error storing audio file: {e}")
        return None

def save_to_mysql(transformed_data):
    """Save transformed data to MySQL"""
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO transcriptions 
            (audio_id, transcript, is_valid, update_date, creation_date, input_source) 
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            transcript = VALUES(transcript),
            is_valid = VALUES(is_valid),
            update_date = VALUES(update_date),
            input_source = VALUES(input_source)
        """
        
        cursor.execute(query, (
            transformed_data['audio_id'],
            transformed_data['transcript'], 
            transformed_data['is_valid'],
            transformed_data['update_date'],
            transformed_data['creation_date'],
            transformed_data['input_source']
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Saved data to MySQL for audio_id: {transformed_data['audio_id']}")
        return True
    except Exception as e:
        logger.error(f"Error saving to MySQL: {e}")
        return False

def transform_youtube_data(raw_data):
    """Transform YouTube data to standard format"""
    audio_id = f"yt-{uuid.uuid4()}"
    
    # In a real implementation, you might extract audio from YouTube
    # using the video_url and time ranges
    # Here we're just creating a mock reference
    audio_url = None
    if 'video_url' in raw_data:
        # Logic to extract audio would go here
        # For now, we'll just note that we would need to extract it
        logger.info(f"Would extract audio from YouTube URL: {raw_data['video_url']}")
        audio_url = f"mock_extracted_from_{raw_data['video_url']}"
    
    return {
        'audio_id': audio_id,
        'transcript': raw_data.get('transcript', ''),
        'is_valid': raw_data.get('is_valid', False),
        'update_date': raw_data.get('update_date', datetime.now().isoformat()),
        'creation_date': raw_data.get('creation_date', datetime.now().isoformat()),
        'input_source': 'youtube',
        'audio_url': audio_url
    }

def transform_custom_api_data(raw_data):
    """Transform custom API data to standard format"""
    audio_id = f"custom-{uuid.uuid4()}"
    
    # Store audio file if present
    audio_url = None
    if 'audio_bytes' in raw_data:
        audio_url = store_audio_file(raw_data['audio_bytes'], audio_id)
    
    return {
        'audio_id': audio_id,
        'transcript': raw_data.get('transcript', ''),
        'is_valid': raw_data.get('is_valid', False),
        'update_date': raw_data.get('update_date', datetime.now().isoformat()),
        'creation_date': raw_data.get('creation_date', datetime.now().isoformat()),
        'input_source': 'custom',
        'audio_url': audio_url
    }

def transform_data(raw_data):
    """Transform raw data based on source"""
    try:
        source = raw_data.get('input_source', '').lower()
        
        if source == 'youtube':
            return transform_youtube_data(raw_data)
        elif source == 'custom':
            return transform_custom_api_data(raw_data)
        else:
            logger.warning(f"Unknown source: {source}")
            return None
    except Exception as e:
        logger.error(f"Error transforming data: {e}")
        return None

def main():
    """Main transformer loop"""
    logger.info("Starting transformer service")
    
    # Ensure MinIO bucket exists
    ensure_bucket_exists()
    
    for message in consumer:
        try:
            raw_data = message.value
            logger.info(f"Received message from {raw_data.get('input_source', 'unknown')}")
            
            # Transform data
            transformed_data = transform_data(raw_data)
            if not transformed_data:
                continue
                
            # Save to MySQL
            save_to_mysql(transformed_data)
            
            # Forward to next service
            producer.send(KAFKA_TOPIC_OUTPUT, transformed_data)
            producer.flush()
            
            logger.info(f"Processed record: {transformed_data['audio_id']}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")

if __name__ == "__main__":
    # Allow time for services to start
    time.sleep(10)
    main()