# Multi-stage build for combined Backend + Nginx
FROM python:3.9-slim

# Install system dependencies including nginx and supervisor
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy backend application
COPY backend/ .

# Copy .env file (QUICK FIX - bundle environment variables)
COPY .env /app/.env

# Copy nginx configuration
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
RUN rm /etc/nginx/sites-enabled/default

# Create directories for static, media, and database
RUN mkdir -p /app/static /app/media /app/data

# Run Django setup commands
RUN python manage.py collectstatic --noinput || true

# Create supervisor configuration to run both Gunicorn and Nginx
RUN mkdir -p /var/log/supervisor
RUN echo '[supervisord]\n\
nodaemon=true\n\
logfile=/var/log/supervisor/supervisord.log\n\
pidfile=/var/run/supervisord.pid\n\
\n\
[program:django]\n\
command=sh -c "python manage.py migrate && python manage.py loaddata categories || true && gunicorn social_media.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --access-logfile - --error-logfile -"\n\
directory=/app\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n\
environment=PYTHONUNBUFFERED=1,PYTHONDONTWRITEBYTECODE=1\n\
\n\
[program:nginx]\n\
command=nginx -g "daemon off;"\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0' > /etc/supervisor/conf.d/supervisord.conf

# Expose port 80 (nginx will serve on this port)
EXPOSE 80

# Start supervisor to manage both services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
