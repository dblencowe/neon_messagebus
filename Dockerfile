FROM python:3.8

LABEL vendor=neon.ai \
    ai.neon.name="neon-messagebus"

ADD . /neon_core
WORKDIR /neon_core

RUN apt-get update && \
    apt-get install -y \
    gcc \
    python3-dev \
    swig \
    libssl-dev  \
    libfann-dev \
    && pip install wheel \
    && pip install .

EXPOSE 8181
EXPOSE 8080

CMD ["neon_messagebus_service"]