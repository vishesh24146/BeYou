# nginx/Dockerfile
FROM nginx:alpine

# Create necessary directories
RUN mkdir -p /etc/nginx/conf.d

# Copy Nginx config file
COPY default.conf /etc/nginx/conf.d/default.conf

# Expose port 80 (HTTP)
EXPOSE 80

# Default command
CMD ["nginx", "-g", "daemon off;"]
