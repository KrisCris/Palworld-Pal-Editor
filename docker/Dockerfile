# Use an official Python runtime as a parent image
# FROM python:3.11-slim
FROM nikolaik/python-nodejs:python3.12-nodejs21-slim

# Define environment variables for customization
# ENV TZ=UTC \
#     PUID=1000 \
#     PGID=1000 \
#     APP_PORT=8000 \
#     APP_LANG=en \
#     LANG=C.UTF-8 \
#     PYTHONUNBUFFERED=1 \
#     MODE=--cli \
#     SAVE_PATH="/mnt/gamesave" \
#     PASSWORD=null

# Set the working directory in the container
WORKDIR /app

# Install dependencies required for managing permissions and timezone
RUN apt-get update && apt-get install -y --no-install-recommends \
        tini \
        gosu \
        tzdata \
    # && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    # && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/* 

# https://github.com/nikolaik/docker-python-nodejs
# All images have a default user `pn`` with uid 1000 and gid 1000.
# Create the appuser user and group before setting permissions
# RUN groupadd -g 1000 appuser && \
#     useradd -m -u 1000 -g appuser -s /bin/bash appuser

# Copy the application's requirements.txt and setup script, then install Python dependencies
# COPY ./requirements.txt ./
# RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's source code
COPY ./ /app

# Copy the entrypoint script into the image and make it executable
COPY ./docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
RUN chmod +x /app/setup_and_run.sh

ENTRYPOINT ["/entrypoint.sh"]

# Expose the port dynamically
EXPOSE $APP_PORT

CMD ["./setup_and_run.sh"]
