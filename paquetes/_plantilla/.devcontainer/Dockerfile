FROM mcr.microsoft.com/devcontainers/python:3.13-bookworm

# Cliente de PostgreSQL (psql) para la base local de pruebas
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

# uv (gestor de Python)
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /uvx /usr/local/bin/

# Carpetas que se montan como volúmenes persistentes: se crean aquí para que pertenezcan a vscode
RUN mkdir -p /home/vscode/.claude /home/vscode/.commandhistory \
 && chown -R vscode:vscode /home/vscode/.claude /home/vscode/.commandhistory \
 && echo 'export HISTFILE=/home/vscode/.commandhistory/.bash_history PROMPT_COMMAND="history -a"' >> /home/vscode/.bashrc
