# ============================================================
#  Smart Stick — top-level Makefile
#  Works on Windows (Git Bash / MSYS2 make) and Linux/macOS.
#
#  Two primary workflows:
#    make rpi-mock + make phone-dev   — laptop mock server + Expo
#    make rpi-real + make phone-dev   — real RPi over SSH + Expo
# ============================================================

# ── Configurable variables ──────────────────────────────────
# Laptop LAN IP (auto-detected; override if wrong).
LAPTOP_IP ?= $(shell python -c \
  "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); \
   s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()" 2>/dev/null)

# Real RPi connection (override via env or CLI).
RPI_HOST ?= raspberrypi.local
RPI_USER ?= pi
RPI_PORT ?= 5000
RPI_DIR  ?= /home/$(RPI_USER)/smart-stick/rpi

# Paths
RPI_DIR_LOCAL := rpi
MOCK_DIR      := mock
MOBILE_DIR    := smart-stick-mobile
VENV          := .venv

# Python / pip from the root venv
ifeq ($(OS),Windows_NT)
  PY  := $(VENV)\Scripts\python
  PIP := $(VENV)\Scripts\pip
else
  PY  := $(VENV)/bin/python
  PIP := $(VENV)/bin/pip
endif

.DEFAULT_GOAL := help

# ============================================================
#  HELP
# ============================================================

.PHONY: help
help:
	@echo ""
	@echo "  Smart Stick — available targets"
	@echo ""
	@echo "  LAPTOP / MOCK WORKFLOW (no hardware)"
	@echo "    make install         Install Python + npm deps"
	@echo "    make rpi-mock        Start backend with fake sensor data"
	@echo "    make phone-dev       Start Expo dev server"
	@echo ""
	@echo "  REAL RPi WORKFLOW  (run from laptop, talks to Pi via SSH)"
	@echo "    make rpi-deploy      rsync rpi/ to the Pi over SSH"
	@echo "    make rpi-real        Deploy + start uvicorn on the Pi"
	@echo "    make rpi-logs        Tail systemd service log on Pi"
	@echo "    make rpi-stop        Stop systemd service on Pi"
	@echo "    make rpi-restart     Restart systemd service on Pi"
	@echo ""
	@echo "  ON-DEVICE TARGETS  (run from inside the Pi, repo root)"
	@echo "    make pi-check-cam    Test OpenCV can grab a frame (INDEX=0)"
	@echo "    make pi-fetch-model  Pre-download yolov8n.pt"
	@echo "    make pi-serve        Start the backend in the foreground"
	@echo "    make pi-health       Curl the local health endpoint"
	@echo ""
	@echo "  DEVELOPMENT"
	@echo "    make test            Run pytest (no hardware)"
	@echo "    make lint            Run ruff"
	@echo "    make fmt             Auto-fix with ruff"
	@echo "    make db-clean        Delete local SQLite database"
	@echo "    make clean           Remove caches, db, node_modules"
	@echo ""
	@echo "  VARIABLES (override on CLI)"
	@echo "    LAPTOP_IP=$(LAPTOP_IP)"
	@echo "    RPI_HOST=$(RPI_HOST)  RPI_USER=$(RPI_USER)  RPI_PORT=$(RPI_PORT)"
	@echo ""

# ============================================================
#  INSTALL  (Python deps + npm — no venv creation)
# ============================================================

.PHONY: install install-rpi install-mobile

install-rpi:
	$(PIP) install --upgrade pip -q
	$(PIP) install -r $(RPI_DIR_LOCAL)/requirements.txt -q
	@echo "Python deps installed"

install-mobile:
	cd $(MOBILE_DIR) && npm install --legacy-peer-deps
	@echo "npm deps installed"

install: install-rpi install-mobile

# ============================================================
#  MOCK WORKFLOW  (Windows laptop, no hardware)
# ============================================================

.PHONY: env-mock rpi-mock

env-mock:
	@python -c "open('$(MOBILE_DIR)/.env.local','w').write('EXPO_PUBLIC_API_BASE_URL=http://$(LAPTOP_IP):$(RPI_PORT)\n')"
	@echo "Mobile API URL -> http://$(LAPTOP_IP):$(RPI_PORT)"

rpi-mock: env-mock
	@echo "Starting mock server on http://$(LAPTOP_IP):$(RPI_PORT) ..."
	$(PY) $(MOCK_DIR)/run.py

# ============================================================
#  REAL RPi WORKFLOW
# ============================================================

.PHONY: env-real rpi-deploy rpi-real rpi-logs rpi-stop rpi-restart

env-real:
	@python -c "open('$(MOBILE_DIR)/.env.local','w').write('EXPO_PUBLIC_API_BASE_URL=http://$(RPI_HOST):$(RPI_PORT)\n')"
	@echo "Mobile API URL -> http://$(RPI_HOST):$(RPI_PORT)"

rpi-deploy:
	@echo "Syncing rpi/ -> $(RPI_USER)@$(RPI_HOST):$(RPI_DIR) ..."
	rsync -avz \
	  --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
	  --exclude '.pytest_cache' --exclude 'data/' \
	  $(RPI_DIR_LOCAL)/ $(RPI_USER)@$(RPI_HOST):$(RPI_DIR)/
	@echo "Sync complete"

rpi-real: env-real rpi-deploy
	@echo "Starting uvicorn on $(RPI_HOST):$(RPI_PORT) ..."
	ssh -t $(RPI_USER)@$(RPI_HOST) \
	  "cd $(RPI_DIR) && \
	   python3 -m venv .venv && \
	   .venv/bin/pip install -r requirements.txt -q && \
	   .venv/bin/uvicorn api.app:create_app --factory \
	     --host 0.0.0.0 --port $(RPI_PORT) --log-level info"

rpi-logs:
	ssh $(RPI_USER)@$(RPI_HOST) "journalctl -u smartstick -f"

rpi-stop:
	ssh $(RPI_USER)@$(RPI_HOST) "sudo systemctl stop smartstick"

rpi-restart:
	ssh $(RPI_USER)@$(RPI_HOST) "sudo systemctl restart smartstick"

# ============================================================
#  ON-DEVICE TARGETS  (run these directly on the Pi)
#
#  Use these when SSH'd into the Pi inside the repo root.
#  Assumes a Python venv at ./rpi/.venv (created during install).
# ============================================================

.PHONY: pi-check-cam pi-fetch-model pi-serve pi-health

# Verify OpenCV can grab a frame from the default camera (override INDEX=1, etc.)
INDEX ?= 0
pi-check-cam:
	cd $(RPI_DIR_LOCAL) && .venv/bin/python -c "import cv2; c=cv2.VideoCapture($(INDEX)); ok,f=c.read(); print('OK' if ok else 'FAIL', None if f is None else f.shape); c.release()"

# Pre-download the YOLO weights so the first inference call doesn't block.
pi-fetch-model:
	cd $(RPI_DIR_LOCAL) && .venv/bin/python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
	@echo "yolov8n.pt cached"

# Start the backend in the foreground on the Pi (Ctrl+C to stop).
pi-serve:
	cd $(RPI_DIR_LOCAL) && .venv/bin/uvicorn api.app:create_app --factory \
	  --host 0.0.0.0 --port $(RPI_PORT) --log-level info

# Hit the local health endpoint to confirm the server is up.
pi-health:
	curl -s http://127.0.0.1:$(RPI_PORT)/api/health

# ============================================================
#  MOBILE APP
# ============================================================

.PHONY: phone-dev phone-android phone-ios

phone-dev: install-mobile
	cd $(MOBILE_DIR) && npx expo start

phone-android: install-mobile
	cd $(MOBILE_DIR) && npx expo start --android

phone-ios: install-mobile
	cd $(MOBILE_DIR) && npx expo start --ios

# ============================================================
#  TESTING & LINTING
# ============================================================

.PHONY: test lint fmt

test:
	cd $(RPI_DIR_LOCAL) && $(PY) -m pytest

lint:
	cd $(RPI_DIR_LOCAL) && $(PY) -m ruff check .

fmt:
	cd $(RPI_DIR_LOCAL) && $(PY) -m ruff check . --fix

# ============================================================
#  CLEANUP
# ============================================================

.PHONY: db-clean clean

db-clean:
	rm -f $(RPI_DIR_LOCAL)/data/smartstick.db
	@echo "local database removed"

clean: db-clean
	find $(RPI_DIR_LOCAL) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(RPI_DIR_LOCAL) -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find $(RPI_DIR_LOCAL) -type d -name .ruff_cache   -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(MOBILE_DIR)/node_modules
	@echo "clean complete"
