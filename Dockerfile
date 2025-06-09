FROM python:3.12-slim as python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBITECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"


FROM python-base as builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    nano \ 
    curl \
    ffmpeg
# WORKDIR $POETRY_HOME
ENV POETRY_VERSION=2.1.3
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 -

WORKDIR $PYSETUP_PATH
COPY ./pyproject.toml ./poetry.lock ./

COPY . .

EXPOSE 8000

# RUN poetry build
RUN poetry install

CMD poetry run python src/main.py