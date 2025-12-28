####################################################################################################
# Frontend Builder
####################################################################################################
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build frontend for production
RUN npm run build

####################################################################################################
# Python Base Image
####################################################################################################
FROM ubuntu:22.04 AS python-base

# Update base image packages
RUN apt-get update && apt-get install -y ca-certificates && \
    apt-get update && apt-get upgrade -y

# Install Python, Node.js & other dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry for dependency management
RUN python3 -m pip install poetry

# Define Poetry's environment variables
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VENV=/opt/poetry-venv
ENV PATH="${POETRY_VENV}/bin:${PATH}"

# Set the working directory
WORKDIR /fd

####################################################################################################
# Backend Builder
####################################################################################################
FROM python-base AS backend-builder

# Copy backend dependency files
COPY backend/pyproject.toml backend/poetry.lock /fd/

# Install backend dependencies
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true \
    && poetry install --without dev --no-root

####################################################################################################
# Production Image (Monolithic: Backend serves Frontend)
####################################################################################################
FROM python-base AS prod

# Copy the virtual environment from the builder stage
COPY --from=backend-builder /fd/.venv ${POETRY_VENV}

# Copy backend source code
COPY backend/fourdrinier/alembic.ini /fd/alembic.ini
COPY backend/fourdrinier /fd/backend/fourdrinier

# Copy frontend build artifacts from frontend-builder
COPY --from=frontend-builder /app/frontend/dist /fd/frontend/dist

# Set PYTHONPATH so Python can find the fourdrinier module
ENV PYTHONPATH=/fd/backend

# Expose backend port (backend will serve frontend static files in production)
EXPOSE 8000

# Run the FastAPI server
CMD python3 -m alembic upgrade head && python -m uvicorn fourdrinier.main:app --host 0.0.0.0 --port 8000

####################################################################################################
# Backend Debug Image (Hot Reloading)
####################################################################################################
FROM python-base AS backend-debug

# Copy the virtual environment from the builder stage
COPY --from=backend-builder /fd/.venv ${POETRY_VENV}

# Install dev dependencies for backend
COPY backend/pyproject.toml backend/poetry.lock /fd/
RUN poetry install --with dev --no-root

# Copy backend source code (will be overridden by volume mount)
COPY backend/fourdrinier/alembic.ini /fd/alembic.ini
COPY backend/fourdrinier /fd/backend/fourdrinier

# Set PYTHONPATH so Python can find the fourdrinier module
ENV PYTHONPATH=/fd/backend

EXPOSE 8000

# Run backend with auto-reload
CMD python3 -m alembic upgrade head && python -m uvicorn fourdrinier.main:app --reload --host 0.0.0.0 --port 8000

####################################################################################################
# Frontend Debug Image (Hot Reloading)
####################################################################################################
FROM node:20-slim AS frontend-debug

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source (will be overridden by volume mount)
COPY frontend/ ./

EXPOSE 3000

# Run frontend dev server with hot reloading
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

####################################################################################################
# Test Image Builder
####################################################################################################
FROM python-base AS build_test

# Copy the virtual environment from the backend-builder stage
COPY --from=backend-builder /fd/.venv /fd/.venv

# Install test dependencies
COPY backend/pyproject.toml backend/poetry.lock /fd/
RUN poetry install --only dev --no-root

####################################################################################################
# Test Image
####################################################################################################
FROM python-base AS test

# Copy the virtual environment from the build_test stage
COPY --from=build_test /fd/.venv /fd/.venv
COPY --from=build_test /fd/.venv ${POETRY_VENV}

# Copy backend source code
COPY backend/fourdrinier/alembic.ini /fd/alembic.ini
COPY backend/fourdrinier /fd/backend/fourdrinier

# Copy in the scripts and tests
COPY backend/scripts /fd/backend/scripts
COPY backend/test /fd/backend/tests
COPY backend/test/pytest.ini /fd/
COPY backend/test/.coveragerc /fd/

# Set PYTHONPATH so Python can find the fourdrinier module
ENV PYTHONPATH=/fd/backend

EXPOSE 8000

# Run the FastAPI server
CMD python3 -m alembic upgrade head && python -m uvicorn fourdrinier.main:app --reload --host 0.0.0.0 --port 8000
