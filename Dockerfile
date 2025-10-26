FROM python:3.10-slim

# Install system dependencies for Playwright/Chromium
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libasound2 \
    libglib2.0-0 \
    libglib2.0-dev \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Install Playwright and Chromium browser binaries
RUN playwright install
RUN playwright install-deps

# Copy your app code
COPY app.py .
COPY form_automation.py .

# Expose the Streamlit default port
EXPOSE 7860

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
