# Makefile

# Use shell command interpreter
SHELL := /bin/bash

# Docker configurations
PRODUCTION_CONFIG = --profile production
TESTING_CONFIG = --profile testing
DEBUG_CONFIG = --profile debug

ALEMBIC_TAG ?= "initial revision"

# Define targets
.PHONY: build-backend build-backend-test run prepare-cache test cleanup revision

# Build the backend
build-backend:
	@echo "Building the .."
	@docker compose $(PRODUCTION_CONFIG) build backend

build-backend-test:
	@echo "Building the backend for testing..."
	@docker compose $(TESTING_CONFIG) build backend_test

# Run the application
run: build-backend
	@echo "Running the application..."
	@docker compose $(PRODUCTION_CONFIG) up --build

prepare-cache:
	@echo "Preparing PyTest cache..."
	@mkdir -p $(PWD)/.pytest_cache

debug: prepare-cache
	@echo "Running the application in debug mode..."
	@docker compose $(DEBUG_CONFIG) up --build

# Run the application tests
test: prepare-cache build-backend-test
	@echo "Running the application for testing..."
	@docker compose $(TESTING_CONFIG) run --rm --volume $(PWD)/.pytest_cache:/fd/.pytest_cache --volume $(PWD)/tmp:/fd/tmp backend_test python -m pytest --cov=backend --cov-branch --cov-report term
	@docker compose $(TESTING_CONFIG) down --volumes

# Run the application tests in verbose mode for debugging
test-verbose: prepare-cache build-backend-test
	@echo "Running the application for testing..."
	@docker compose $(TESTING_CONFIG) run --rm --volume $(PWD)/backend/fourdrinier/alembic/versions:/fd/backend/fourdrinier/alembic/versions backend_test python -m alembic upgrade head
	@docker compose $(TESTING_CONFIG) run --rm --volume $(PWD)/.pytest_cache:/fd/.pytest_cache --volume $(PWD)/tmp:/fd/tmp backend_test python -m pytest -vvv --cov=backend --cov-branch --cov-report term
	@docker compose $(TESTING_CONFIG) down --volumes

# Remove containers and volumes
cleanup:
	@echo "Cleaning up..."
	@docker compose $(PRODUCTION_CONFIG) down --volumes
	@docker compose $(TESTING_CONFIG) down --volumes
	@docker compose $(DEBUG_CONFIG) down --volumes

# Generate an Alembic revision file
revision: build-backend
	@echo "Creating a new revision..."
	- docker compose $(TESTING_CONFIG) down --volumes
	@docker compose $(TESTING_CONFIG) run --rm --volume $(PWD)/backend/fourdrinier/alembic/versions:/fd/backend/fourdrinier/alembic/versions --entrypoint /fd/backend/scripts/generate_revision.sh backend $(ALEMBIC_TAG)
	- docker compose $(TESTING_CONFIG) down --volumes