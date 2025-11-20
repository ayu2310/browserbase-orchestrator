FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables (override in deployment)
ENV DATABASE_PATH=/tmp/workflows.db
ENV PORT=8000

# Run API server
CMD ["python", "api_server.py"]

