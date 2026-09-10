FROM node:22-alpine
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund
COPY lib ./lib
COPY worker ./worker
RUN mkdir -p /app/storage && chown -R node:node /app/storage
ENV NODE_ENV=production \
    DEUS_LIFE_STATE_PATH=/app/storage/deus-life-state.json \
    DEUS_LIFE_JOURNAL_PATH=/app/storage/deus-life-events.ndjson \
    DEUS_LIFE_PULSE_MS=20000
USER node
VOLUME ["/app/storage"]
CMD ["node", "worker/life-daemon.mjs"]
