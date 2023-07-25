FROM python:3.8-slim

LABEL vendor=neon.ai \
    ai.neon.name="neon-messagebus"

ENV OVOS_CONFIG_BASE_FOLDER neon
ENV OVOS_CONFIG_FILENAME neon.yaml
ENV XDG_CONFIG_HOME /config

EXPOSE 8181

RUN apt update && \
    apt install -y \
    gcc \
    python3-dev \
    swig \
    libssl-dev

ADD . /neon_messagebus
WORKDIR /neon_messagebus

RUN pip install wheel \
    && pip install .

COPY docker_overlay/ /

CMD ["neon-messagebus", "run"]