FROM nikolaik/python-nodejs:python3.12-nodejs21-slim

ENV PATH=/usr/local/nginx/bin:$PATH
EXPOSE 58888
VOLUME [ "/mnt/gamesave" ]

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        tini \
        gosu \
    && apt-get clean && rm -rf /var/lib/apt/lists/* 

COPY --chown=pn:pn --chmod=777 ./ /app

RUN cd "/app/frontend/palworld-pal-editor-webui" \
    && npm install \
    && npm run build \
    && mv "/app/frontend/palworld-pal-editor-webui/dist" "/app/src/palworld_pal_editor/webui" 

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install -e .

RUN chmod +x /app/docker/app.sh

ENTRYPOINT ["tini", "-g", "--"]

CMD ["/app/docker/app.sh"]