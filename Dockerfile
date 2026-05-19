# BeautyOS-Hermes bootstrap image (scaffold)
#
# This Dockerfile is the *thin-wrapper* layer. In a full deployment it
# would FROM an upstream Hermes image and overlay our bootstrap. For
# now (Phase-3 step 3) it only contains the bootstrap so we can run
# the smoke against a live BeautyOS stack without pulling all of
# upstream Hermes.
#
# Build:
#   docker build -t beautyos-hermes:local .
# Run (against compose stack on host):
#   docker run --rm --network ai-beautyos_beautyos-internal \
#     -e BEAUTYOS_BASE=http://web:3000 \
#     -e TOOL_BASE=http://tool-server:5001 \
#     beautyos-hermes:local

FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir pyyaml==6.0.2

COPY bootstrap.py /app/bootstrap.py
COPY config /app/config
COPY UPSTREAM_HERMES.txt /app/UPSTREAM_HERMES.txt

ENV BEAUTYOS_BASE=http://web:3000 \
    TOOL_BASE=http://tool-server:5001 \
    BEAUTYOS_AGENT_ID=hermes-bootstrap

ENTRYPOINT ["python3", "/app/bootstrap.py"]

LABEL org.opencontainers.image.title="beautyos-hermes" \
      org.opencontainers.image.source="https://github.com/CHINGBOH/beautyos-hermes" \
      org.opencontainers.image.licenses="MIT"
