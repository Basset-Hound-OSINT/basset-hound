# Dockerfile for Flask App

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Check if requirements.txt exists and copy it
COPY requirements.txt /app/ 2>/dev/null
RUN [ -f /app/requirements.txt ] && pip install --no-cache-dir -r /app/requirements.txt || echo "No requirements.txt found"

# Copy the application code
COPY . /app/

# Expose port
EXPOSE 5000

# Command to run the Flask app
CMD ["python", "app.py"]
