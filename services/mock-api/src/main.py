# services/mock-api/src/main.py
import os
import json
import time
import random
import base64
import datetime
from flask import Flask, jsonify

app = Flask(__name__)

SAMPLE_DATA_PATH = os.getenv('SAMPLE_DATA_PATH', '/app/sample-data')

# Load sample audio data
def load_sample_audio():
    audio_files = []
    try:
        # Load some placeholder audio bytes
        for i in range(1, 4):
            sample_path = f"{SAMPLE_DATA_PATH}/sample{i}.wav"
            if os.path.exists(sample_path):
                with open(sample_path, 'rb') as f:
                    audio_bytes = base64.b64encode(f.read()).decode('utf-8')
                    audio_files.append(audio_bytes)
            else:
                # Generate random noise as placeholder audio
                audio_bytes = base64.b64encode(os.urandom(5000)).decode('utf-8')
                audio_files.append(audio_bytes)
    except Exception as e:
        print(f"Error loading sample audio: {e}")
        # Fallback to dummy data
        audio_files = [base64.b64encode(os.urandom(5000)).decode('utf-8') for _ in range(3)]
    
    return audio_files

SAMPLE_AUDIOS = load_sample_audio()

# Sample transcripts
SAMPLE_TRANSCRIPTS = [
    "This is a test transcript for the mock API service.",
    "The quick brown fox jumps over the lazy dog.",
    "Machine learning models need large datasets for training.",
    "Cloud computing offers scalable solutions for businesses.",
    "Artificial intelligence is transforming many industries.",
    "Data privacy remains an important concern in tech.",
    "Natural language processing improves human-computer interaction."
]

@app.route('/transcripts', methods=['GET'])
def get_transcripts():
    """Return random transcripts to simulate API responses"""
    current_time = datetime.datetime.now()
    
    # Generate 1-3 random transcripts
    num_transcripts = random.randint(1, 3)
    transcripts = []
    
    for _ in range(num_transcripts):
        # Create a random transcript
        transcript_text = random.choice(SAMPLE_TRANSCRIPTS)
        is_valid = random.random() > 0.2  # 80% valid
        creation_date = (current_time - datetime.timedelta(days=random.randint(0, 30))).isoformat()
        update_date = current_time.isoformat()
        
        # Use sample audio or generate random audio bytes
        audio_bytes = random.choice(SAMPLE_AUDIOS)
        
        transcripts.append({
            'audio_bytes': audio_bytes,
            'transcript': transcript_text,
            'is_valid': is_valid,
            'update_date': update_date,
            'creation_date': creation_date
        })
    
    return jsonify(transcripts)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    # Wait for other services to be ready
    time.sleep(5)
    app.run(host='0.0.0.0', port=8080)