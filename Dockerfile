FROM python:3.11-slim

WORKDIR /app

# Copia os arquivos do projeto
COPY pyproject.toml README.md run_demo.py app_server.py ./
COPY audit_ops ./audit_ops
COPY knowledge_base ./knowledge_base
COPY samples ./samples
COPY web ./web
COPY tests ./tests

# Instala dependências para modo ADK Live + Conector PostgreSQL/AlloyDB na nuvem
# Sem `|| true`: se o ADK não instalar, o build deve falhar em vez de publicar uma imagem só-simulação
RUN pip install --no-cache-dir "pydantic>=2.0" python-dotenv "google-genai>=1.30" "google-adk>=2.13,<3" psycopg2-binary

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV GEMINI_LOCATION=global
ENV MODEL_TIER_FAST=gemini-3.8-flash
ENV MODEL_TIER_STANDARD=gemini-3.8-flash
ENV MODEL_TIER_REASONING=gemini-3.1-pro-preview

EXPOSE 8080

CMD ["python3", "app_server.py"]
