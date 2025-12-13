# Use a slim python image for efficiency
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed (e.g., for certain tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Prettier globally (often required for format tasks)
RUN npm install -g prettier@3.4.2

# Copy requirements and install python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create the data directory for file operations
RUN mkdir -p /data

# Expose the port
EXPOSE 8000

# Command to run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
