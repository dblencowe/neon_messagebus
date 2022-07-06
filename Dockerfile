FROM python:3.8-slim

LABEL vendor=neon.ai \
    ai.neon.name="neon-messagebus"

ENV NEON_CONFIG_PATH /config

EXPOSE 8181

RUN apt-get update && \
    apt-get install -y \
    gcc \
    python3-dev \
    swig \
    libssl-dev

ADD . /neon_messagebus
WORKDIR /neon_messagebus

RUN pip install wheel \
    && pip install .

COPY docker_overlay/ /

CMD ["neon_messagebus_service"]