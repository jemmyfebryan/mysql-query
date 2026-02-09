# Makefile for FastAPI project

# Variables
IMAGE_NAME=mysql-db-app
PORT=8085
CONTAINER_NAME=mysql-db-container
USE_DOCKER ?= false

# Python virtual environment settings
VENV_DIR=.venv
PYTHON=$(VENV_DIR)/bin/python
PIP=$(VENV_DIR)/bin/pip

.PHONY: build run stop remove logs shell restart rebuild venv

# Create virtual environment if it doesn't exist
venv:
	@test -d $(VENV_DIR) || (python3 -m venv $(VENV_DIR) && $(PIP) install --upgrade pip && $(PIP) install -r requirements.txt)

# Build Docker image (Only relevant for Docker mode)
build:
ifeq ($(USE_DOCKER),true)
	docker build -t $(IMAGE_NAME) .
else
	@echo "Build step skipped: USE_DOCKER is false (running via PM2)"
endif

# Run the application
run:
ifeq ($(USE_DOCKER),true)
	docker run -d -p $(PORT):$(PORT) --name $(CONTAINER_NAME) $(IMAGE_NAME)
else
	$(MAKE) venv
	pm2 start $(PYTHON) --name $(CONTAINER_NAME) -- -m uvicorn main:app --host 0.0.0.0 --port $(PORT)
endif

# Stop the application
stop:
ifeq ($(USE_DOCKER),true)
	docker stop $(CONTAINER_NAME) || true
else
	pm2 stop $(CONTAINER_NAME) || true
endif

# Remove the application/container
remove:
ifeq ($(USE_DOCKER),true)
	docker rm $(CONTAINER_NAME) || true
else
	pm2 delete $(CONTAINER_NAME) || true
endif

# View logs
logs:
ifeq ($(USE_DOCKER),true)
	docker logs -f $(CONTAINER_NAME)
else
	pm2 logs $(CONTAINER_NAME)
endif

# Access shell (Docker only)
shell:
ifeq ($(USE_DOCKER),true)
	docker exec -it $(CONTAINER_NAME) /bin/sh
else
	@echo "Shell command is only available in Docker mode."
endif

# Rebuild and restart
rebuild: stop remove build run

# Restart
restart: stop run