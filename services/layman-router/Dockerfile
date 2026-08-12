FROM python:3.14.3-slim@sha256:5e59aae31ff0e87511226be8e2b94d78c58f05216efda3b07dbbed938ec8583b

WORKDIR /app
COPY services/layman-router/pyproject.toml services/layman-router/README.md services/layman-router/LICENSE services/layman-router/hatch_build.py services/layman-router/requirements.lock ./
COPY services/layman-router/src ./src
COPY services/layman-router/config ./config
COPY .agents/plugins/marketplace.json ./.agents/plugins/marketplace.json
COPY plugins/layman ./plugins/layman
RUN pip install --no-cache-dir --require-hashes -r requirements.lock \
    && pip install --no-cache-dir --no-deps . \
    && pip check

EXPOSE 8787
CMD ["layman", "serve"]
