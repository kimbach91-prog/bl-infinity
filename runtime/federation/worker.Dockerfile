FROM node:22-alpine
WORKDIR /app
COPY package.json ./
COPY lib ./lib
COPY worker ./worker
ENV HOST=0.0.0.0 PORT=8790 NODE_ENV=production
USER node
EXPOSE 8790
CMD ["node", "worker/server.mjs"]
