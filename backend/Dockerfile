# # Dockerfile
# FROM python:3.9-slim

# # Set environment variables
# ENV PYTHONUNBUFFERED=1

# # Set working directory
# WORKDIR /app

# # Copy files
# COPY . .

# # Install dependencies
# RUN pip install --upgrade pip
# RUN pip install -r requirements.txt

# # Run the Django server
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


FROM python:3.9-slim

# 1. Install build dependencies (removed MySQL client since we're using SQLite)
RUN apt-get update && apt-get install -y \
    gcc \
    pkg-config \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 3. Set workdir
WORKDIR /app

# 4. Copy requirements first for better caching
COPY requirements.txt .

# 5. Upgrade pip and install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 6. Copy application code
COPY . .

# 7. Create directories for static and media files
RUN mkdir -p /app/static /app/media

# 8. Collect static files
RUN python manage.py collectstatic --noinput || true

# 9. Expose port
EXPOSE 8000

# 10. Command will be set in docker-compose
