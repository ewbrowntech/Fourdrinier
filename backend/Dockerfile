####################################################################################################
# Base Image
####################################################################################################
FROM ubuntu:22.04 AS base

# Update base image packages
RUN apt-get update && apt-get install -y ca-certificates && \
    apt-get update && apt-get upgrade -y

# Install Python & Curl
RUN apt-get update && apt-get install -y python3 python3-pip curl openssh-client

# Install Poetry for dependency management
RUN python3 -m pip install poetry

# Define Poetry's environment variables
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VENV=/opt/poetry-venv
ENV PATH="${POETRY_VENV}/bin:${PATH}"

# Set the working directory
WORKDIR /fd

# Copy the source code
COPY ./fourdrinier/alembic.ini /fd/alembic.ini
COPY ./fourdrinier /fd/backend/fourdrinier

####################################################################################################
# Base Image Builder
####################################################################################################
FROM base AS builder

# Install root dependencies
COPY pyproject.toml poetry.lock /fd/
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true \
    && poetry install --without dev --no-root

####################################################################################################
# Production Image
####################################################################################################
FROM base AS prod

# Copy the virtual environment from the builder stage
COPY --from=builder /fd/.venv ${POETRY_VENV}

EXPOSE 8000

# Run the FastAPI server
CMD python3 -m alembic upgrade head && python -m uvicorn fourdrinier.main:app --host 0.0.0.0 --port 8000

####################################################################################################
# Test Image Builder
####################################################################################################
FROM base AS build_test

# Copy the virtual environment from the builder stage
COPY --from=builder /fd/.venv /fd/.venv

# Install test dependencies
COPY pyproject.toml poetry.lock /fd/
RUN poetry install --only dev --no-root

####################################################################################################
# Test Image
####################################################################################################
FROM base AS test

# COPY the virtual environment from the build_test stage
COPY --from=build_test /fd/.venv /fd/.venv

# Copy the source code
COPY --from=build_test /fd/.venv ${POETRY_VENV}

# Copy in the scripts
COPY ./scripts /fd/backend/scripts

# Copy in the tests
COPY ./test /fd/backend/tests
COPY ./test/pytest.ini /fd/
COPY ./test/.coveragerc /fd/

EXPOSE 8000

# Run the FastAPI server
CMD python3 -m alembic upgrade head && python -m uvicorn fourdrinier.main:app --reload --host 0.0.0.0 --port 8000