FROM python:3.13-slim

WORKDIR /app

RUN pip install poetry
COPY pyproject.toml poetry.lock /app/

# Install OpenCV dependencies
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0

# Install python dependencies only as a separate layer (for speed in rebuilding)
RUN poetry install --no-root

# Install playwright (this has extra steps due to its dependencies)
RUN poetry run playwright install-deps chromium
RUN poetry run playwright install chromium

COPY ./README.md /app/README.md
COPY ./src /app/src

ENV PYTHONPATH=/app/src

RUN poetry install

CMD ["poetry", "run", "uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8080"]