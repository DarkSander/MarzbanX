ARG PYTHON_VERSION=3.12
ARG NODE_VERSION=20
ARG XRAY_VERSION=v26.9.9

FROM node:${NODE_VERSION}-slim AS frontend

WORKDIR /code/app/dashboard

COPY app/dashboard/package.json app/dashboard/package-lock.json ./
RUN npm ci

COPY app/dashboard/ ./
ENV VITE_BASE_API=/api/
RUN npm run build -- --outDir build --assetsDir statics \
    && cp build/index.html build/404.html

FROM python:$PYTHON_VERSION-slim AS build
ARG XRAY_VERSION

ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl unzip gcc python3-dev libpq-dev \
    && ARCH="$(dpkg --print-architecture)" \
    && case "$ARCH" in \
         amd64) XRAY_ARCH=64 ;; \
         arm64) XRAY_ARCH=arm64-v8a ;; \
         armhf) XRAY_ARCH=arm32-v7a ;; \
         *) echo "Unsupported architecture: $ARCH" >&2 && exit 1 ;; \
       esac \
    && curl -fL -o /tmp/xray.zip "https://github.com/XTLS/Xray-core/releases/download/${XRAY_VERSION}/Xray-linux-${XRAY_ARCH}.zip" \
    && unzip -o /tmp/xray.zip -d /usr/local/bin xray \
    && chmod +x /usr/local/bin/xray \
    && mkdir -p /usr/local/share/xray \
    && curl -fL -o /usr/local/share/xray/geoip.dat "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat" \
    && curl -fL -o /usr/local/share/xray/geosite.dat "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat" \
    && rm -f /tmp/xray.zip \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/
RUN python3 -m pip install --upgrade pip "setuptools<82" \
    && pip install --no-cache-dir --upgrade -r /code/requirements.txt

FROM python:$PYTHON_VERSION-slim

ENV PYTHON_LIB_PATH=/usr/local/lib/python${PYTHON_VERSION%.*}/site-packages
WORKDIR /code

RUN rm -rf $PYTHON_LIB_PATH/*

COPY --from=build $PYTHON_LIB_PATH $PYTHON_LIB_PATH
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /usr/local/share/xray /usr/local/share/xray

COPY . /code
COPY --from=frontend /code/app/dashboard/build /code/app/dashboard/build

RUN ln -s /code/marzban-cli.py /usr/bin/marzban-cli \
    && chmod +x /usr/bin/marzban-cli \
    && marzban-cli completion install --shell bash

CMD ["bash", "-c", "alembic upgrade head; python main.py"]
