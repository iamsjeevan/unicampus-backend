# Dockerfile

# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim-bullseye
# Using python:3.11-slim for a smaller image. Adjust if your local dev uses a different 3.x version.
# Bullseye is a stable Debian release.

# 2. Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1  # Prevents python from writing .pyc files
ENV PYTHONUNBUFFERED 1      # Force stdout/stderr to be unbuffered (good for Docker logs)
ENV FLASK_APP run.py
ENV FLASK_ENV production     # Default to production for built images
# Note: FLASK_DEBUG will typically be 0 or false in production

# 3. Set the working directory in the container
WORKDIR /app

# 4. Install system dependencies (if any) - for now, likely none beyond what python base has
# RUN apt-get update && apt-get install -y --no-install-recommends some-package \
#    && rm -rf /var/lib/apt/lists/*

# 5. Install Python dependencies
# Copy only requirements.txt first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of the application code into the container
COPY . .

# 7. Expose the port the app runs on (Gunicorn will run on 8000 by default if not specified)
EXPOSE 8000

# 8. Define the command to run the application
# Using Gunicorn as a production-ready WSGI server
# You'll need to add 'gunicorn' to your requirements.txt
# Example: 4 workers, binding to all interfaces on port 8000
# The 'application' variable is what Gunicorn looks for by default in run:application
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "run:application"]

# For development, you might override CMD with: CMD ["flask", "run", "--host=0.0.0.0", "--port=8000"]
# But production images should use a proper WSGI server.