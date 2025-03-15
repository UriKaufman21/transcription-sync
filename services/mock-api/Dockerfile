# services/mock-api/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install flask==2.2.3

# Copy service code
COPY src/ .

# Create sample data directory
RUN mkdir -p /app/sample-data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:8080/health || exit 1

# Run service
CMD ["python", "main.py"]