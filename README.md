# Transcription Synchronization System

This system integrates transcription data from multiple sources, transforms it into a standardized format, and synchronizes it across SQL and Elasticsearch databases. It also manages audio storage for transcriptions.

## System Architecture

The system consists of several microservices:

1. **Extractor Service**: Pulls data from YouTube DB and Custom API
2. **Transformer Service**: Standardizes data format and manages audio storage
3. **Sync Service**: Keeps SQL and Elasticsearch databases synchronized
4. **Mock Services**: Simulates data sources for development and testing

Data flows through the system via Kafka messaging, ensuring reliable processing and scalability.

## Project Structure

```
transcription-sync/
├── docker-compose.yml
├── .env.example
├── README.md
├── tests/
│   ├── e2e/
│   ├── integration/
│   └── component/
├── services/
│   ├── extractor/
│   ├── transformer/
│   ├── sync/
│   └── audio-storage/
├── db/
│   ├── migrations/
│   ├── init-scripts/
│   └── schemas/
└── monitoring/
    ├── prometheus/
    └── grafana/
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Git

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/transcription-sync.git
   cd transcription-sync
   ```

2. Create and configure the environment file:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Start the system:
   ```bash
   docker-compose up -d
   ```

4. Monitor the setup process:
   ```bash
   docker-compose logs -f
   ```

### Environment Variables

Configure the following environment variables in your `.env` file:

- `MYSQL_ROOT_PASSWORD`: Password for MySQL root user
- `MOCK_YOUTUBE_DB_PASSWORD`: Password for mock YouTube DB
- `ELASTIC_PASSWORD`: Password for Elasticsearch
- `MINIO_ROOT_USER`: MinIO username
- `MINIO_ROOT_PASSWORD`: MinIO password
- `GRAFANA_ADMIN_USER`: Grafana admin username
- `GRAFANA_ADMIN_PASSWORD`: Grafana admin password

## Running Tests

### End-to-End Tests

To run the end-to-end tests that verify the complete system:

```bash
docker-compose -f docker-compose.yml -f docker-compose.test.yml up test-e2e
```

### Component Tests

To run component tests for individual services:

```bash
docker-compose -f docker-compose.yml -f docker-compose.test.yml up test-component
```

### Integration Tests

To run integration tests between services:

```bash
docker-compose -f docker-compose.yml -f docker-compose.test.yml up test-integration
```

## Monitoring

The system includes monitoring with Prometheus and Grafana:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (login with credentials from `.env`)

## Database Access

- **MySQL**: localhost:3306 (User: root, Password: from `.env`)
- **Elasticsearch**: http://localhost:9200 (User: elastic, Password: from `.env`)
- **MinIO** (Audio Storage): http://localhost:9001 (User/Password: from `.env`)

## Data Model

### Standardized Transcription Format

```json
{
  "audio_id": "unique-identifier",
  "transcript": "The transcribed text content",
  "is_valid": true,
  "update_date": "2023-01-01T12:00:00",
  "creation_date": "2023-01-01T10:00:00",
  "input_source": "youtube|custom",
  "audio_url": "s3://audio-files/unique-identifier.wav"
}
```

## API Endpoints

### Mock Custom API

- `GET /transcripts`: Returns random transcripts
- `GET /health`: Health check endpoint

## Production Deployment

For production deployment, consider the following:

1. Use a production-grade Kafka setup with proper replication
2. Configure proper authentication for all services
3. Implement detailed logging and monitoring
4. Set up backup procedures for databases
5. Use Kubernetes for orchestration instead of Docker Compose
6. Implement CI/CD pipelines for automated testing and deployment

## Troubleshooting

If you encounter issues:

1