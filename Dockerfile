FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set environment variables for Flask/Gunicorn
ENV PYTHONUNBUFFERED=1

# Expose the port that Cloud Run expects (defaults to 8080)
EXPOSE 8080

# Command to run the application using Gunicorn
# Cloud Run injects the $PORT environment variable, so we bind to it
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
