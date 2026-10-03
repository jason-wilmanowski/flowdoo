# syntax=docker/dockerfile:1
# Build context: frontend/. pnpm comes from corepack (version pinned in package.json).

FROM node:22.23.2@sha256:dd5847a04b0deee391fa145f1f4c6d214196668b6bcc7988ebed67249f226844

ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH
RUN corepack enable \
    && mkdir -p /pnpm /app \
    && chown node:node /pnpm /app

USER node
WORKDIR /app

COPY --chown=node:node package.json pnpm-lock.yaml ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store,uid=1000,gid=1000 \
    pnpm install --frozen-lockfile

COPY --chown=node:node . .

EXPOSE 5173
CMD ["pnpm", "dev", "--host", "0.0.0.0", "--port", "5173"]
