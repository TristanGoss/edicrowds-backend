FROM python:3.13-slim

# Poetry install
RUN pip install poetry

# Copy files and install
WORKDIR /engine
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

# Copy app
COPY src/ ./src/

# Set the PYTHONPATH so `engine.main` is importable
ENV PYTHONPATH=/engine/src

CMD ["poetry", "run", "uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8080"]