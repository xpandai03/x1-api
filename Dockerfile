FROM python:3.11-slim

# Install system dependencies for Playwright browsers
RUN apt-get update && \
    apt-get install -y wget gnupg2 libgtk-4-1 libgraphene-1.0-0 libgstgl-1.0-0 \
    libgstcodecparsers-1.0-0 libavif15 libenchant-2-2 libsecret-1-0 \
    libmanette-0.2-0 libgles2 && \
    apt-get clean

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN pip install playwright && playwright install --with-deps

# Copy your source code
COPY . .

# Set the default port for Flask
ENV PORT 8080

CMD ["python3", "roster_api.py"]