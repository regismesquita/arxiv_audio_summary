# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for litellm API key and model (users can override these)
ENV LITELLM_API_KEY=""
ENV MODEL_NAME="mistral-small-latest"

# Set working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000 for the Flask server
EXPOSE 5000

# Command to run the Flask server
CMD ["python", "vibe/main.py", "--serve"]