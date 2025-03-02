# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

COPY ./requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Copy the current directory contents into the container at /app
COPY . .

# Expose port 5000 for the Flask server
EXPOSE 5000

# Command to run the Flask server
CMD ["python", "-m", "vibe.main", "--serve"]
