FROM python:3.11-slim

# Install system dependencies for Playwright browsers
RUN apt-get update && \
    apt-get install -y wget gnupg2 libgtk-3-0 libxss1 libasound2 \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libatspi2.0-0 libxkbcommon0 libxshmfence1 libglu1-mesa && \
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