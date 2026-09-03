FROM node:22-alpine
WORKDIR /app
COPY package.json ./
COPY lib ./lib
COPY adapters ./adapters
COPY worker ./worker
COPY config ./config
COPY dev-server.mjs ./
ENV HOST=0.0.0.0 PORT=8787 NODE_ENV=production
USER node
EXPOSE 8787
CMD ["node", "dev-server.mjs"]
