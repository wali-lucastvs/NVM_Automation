PYTHON ?= python
PIP ?= pip
POWERSHELL ?= powershell

INPUT_TYPE ?= json
INPUT_FILE ?= workspace/input/nvm_blocks.json
OUTPUT_DIR ?= workspace/output
PREVIOUS_ARXML ?= workspace/input/NvM.arxml
AUTOSAR_VERSION ?= Autosar_4_0_2

.PHONY: help install install-dev gui build build-exe test clean
all: clean test build

help:
	@echo Available targets:
	@echo   install                - Install runtime dependencies
	@echo   install-dev            - Install development dependencies
	@echo   gui                    - Launch the desktop GUI
	@echo   build-exe              - Build the executable
	@echo   test                   - Run unit tests
	@echo.
	@echo Variables you can override:
install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements.txt

gui:
	$(PYTHON) -m nvm_app.gui

build:
	$(POWERSHELL) -ExecutionPolicy Bypass -File .\build_exe.ps1

test:
	$(PYTHON) -m unittest discover -s tests -p "test_*.py"

clean:
	$(POWERSHELL) -NoProfile -Command "if (Test-Path 'release') { Remove-Item -Recurse -Force 'release' }"
	$(POWERSHELL) -NoProfile -Command "if (Test-Path '__pycache__') { Remove-Item -Recurse -Force '__pycache__' }"
	$(POWERSHELL) -NoProfile -Command "if (Test-Path 'tests\__pycache__') { Remove-Item -Recurse -Force 'tests\__pycache__' }"
	$(POWERSHELL) -NoProfile -Command "if (Test-Path 'tests\_tmp') { Remove-Item -Recurse -Force 'tests\_tmp' }"
	$(POWERSHELL) -NoProfile -Command "if (Test-Path 'nvm_tool\__pycache__') { Remove-Item -Recurse -Force 'nvm_tool\__pycache__' }"
