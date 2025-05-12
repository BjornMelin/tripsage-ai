FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        wget \
        gnupg \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Crawl4AI and its dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set environment variables
ENV PORT=11235
ENV CRAWL4AI_API_KEY=""
ENV PYTHONUNBUFFERED=1

# Expose the port
EXPOSE 11235

# Run the server
CMD ["python", "server.py"]