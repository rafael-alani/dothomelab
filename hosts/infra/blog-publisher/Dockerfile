FROM node:24-bookworm-slim
WORKDIR /publisher
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts
COPY export.mjs ./
ENTRYPOINT ["node", "export.mjs"]
CMD ["/vault", "/output"]
