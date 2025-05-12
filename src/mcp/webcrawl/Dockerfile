FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        wget \
        gnupg \
        ca-certificates \
        curl \
        git \
        libglib2.0-0 \
        libnss3 \
        libnspr4 \
        libfontconfig1 \
        libxcb1 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxi6 \
        libxrandr2 \
        libxtst6 \
        libgbm1 \
        libasound2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for Playwright (required for some crawling operations)
RUN curl -sS https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Crawl4AI and its dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install --with-deps chromium

# Create directories for logs and cache
RUN mkdir -p logs cache

# Copy the application code
COPY . .

# Set environment variables
ENV PORT=11235
ENV CRAWL4AI_API_KEY=""
ENV FIRECRAWL_API_KEY=""
ENV PYTHONUNBUFFERED=1
ENV REDIS_URL="redis://redis:6379/0"

# Expose the port
EXPOSE 11235

# Run the server
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "11235"]