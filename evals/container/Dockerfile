FROM node:24.11.1-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git python3 ca-certificates ripgrep \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global @mariozechner/pi-coding-agent@0.73.1 opencode-ai@1.19.6 \
        @openai/codex@0.169.0 @anthropic-ai/claude-code@2.1.327 \
    && npm cache clean --force \
    && pi --version \
    && opencode --version \
    && codex --version \
    && claude --version

COPY driver.py smoke.py /opt/herzo-evals/
USER 1000:1000
WORKDIR /work
ENTRYPOINT ["python3", "/opt/herzo-evals/driver.py"]
