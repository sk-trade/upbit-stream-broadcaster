FROM python:3.10-slim

ARG VERSION
ARG LOG_LEVEL
ARG ZMQ_PORT
ARG TOP_TICKERS
ARG MINUTE_INTERVAL
ARG MATTERMOST_URL

ENV VERSION=${VERSION}
ENV LOG_LEVEL=${LOG_LEVEL}
ENV ZMQ_PORT=${ZMQ_PORT}
ENV TOP_TICKERS=${TOP_TICKERS}
ENV MINUTE_INTERVAL=${MINUTE_INTERVAL}
ENV MATTERMOST_URL=${MATTERMOST_URL}

WORKDIR /usr/src/app

COPY . .

RUN apt-get update && apt-get install -y \
    cron \
    fonts-nanum \
    && python -m pip install --upgrade pip \
    && pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-root\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
       
EXPOSE 11555
# 시작 명령
CMD ["python", "-m", "myapp.src.main"]
