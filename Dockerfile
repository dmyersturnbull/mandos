# This is Dockerfile for the server
# https://stackoverflow.com/questions/53835198/integrating-python-poetry-with-docker/54763270#54763270

FROM python:3.9


# --------------------------------------
# ------------- Set labels -------------

# See https://github.com/opencontainers/image-spec/blob/master/annotations.md
LABEL name="mandos"
LABEL version="0.2.0"
LABEL vendor="dmyersturnbull"
LABEL org.opencontainers.image.title="mandos"
LABEL org.opencontainers.image.version="0.2.0"
LABEL org.opencontainers.image.url="https://github.com/dmyersturnbull/mandos"
LABEL org.opencontainers.image.documentation="https://github.com/dmyersturnbull/mandos"


# --------------------------------------
# ---------- Copy and install ----------

# ENV no longer adds a layer in new Docker versions,
# so we don't need to chain these in a single line
ENV PYTHONFAULTHANDLER=1
# no .pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=off
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_DEFAULT_TIMEOUT=120
ENV POETRY_VERSION=1.1.4
#ENV LC_ALL=C.UTF-8
#ENV LANG=C.UTF-8

# Install system deps
RUN pip install "poetry==$POETRY_VERSION"

# Copy only requirements to cache them in docker layer
WORKDIR /code
COPY poetry.lock pyproject.toml /code/

# Install with poetry
# pip install would probably work, too, but we'd have to make sure it's a recent enough pip
# Don't bother creating a virtual env -- significant performance increase
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --no-dev

# Copy to workdir
COPY . /code

RUN poetry install /code --extras server

EXPOSE 1532/tcp
ENTRYPOINT mandos
CMD [":serve", "--init", "--port", "1532", "--log", "serve.log"]
