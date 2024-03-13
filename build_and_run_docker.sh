docker build -t palworld-pal-editor -f docker/Dockerfile .

if which docker-compose > /dev/null; then
    docker-compose -f docker/docker-compose.yml up -d
else
    docker compose -f docker/docker-compose.yml up -d
fi