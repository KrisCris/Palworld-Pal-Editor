FROM nikolaik/python-nodejs:python3.12-nodejs21-slim

ENV PATH=/usr/local/nginx/bin:$PATH
EXPOSE $APP_PORT

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        tini \
        gosu \
        tzdata \
    && apt-get clean && rm -rf /var/lib/apt/lists/* 

COPY --chown=pn:pn ./ /app

RUN cd "/app/frontend/palworld-pal-editor-webui" \
    && npm install \
    && npm run build \
    && mv "/app/frontend/palworld-pal-editor-webui/dist" "/app/src/palworld_pal_editor/webui" 

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install -e .

RUN chmod +x /app/docker/app.sh

CMD ["/app/docker/app.sh"]