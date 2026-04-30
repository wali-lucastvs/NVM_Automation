PYTHON ?= python
PIP ?= pip
POWERSHELL ?= powershell

# Command to remove directories; default to POSIX `rm -rf` but can be overridden on Windows
RM_DIR ?= rm -rf

INPUT_TYPE ?= json
INPUT_FILE ?= workspace/input/nvm_blocks.json
OUTPUT_DIR ?= workspace/output
PREVIOUS_ARXML ?= workspace/input/NvM.arxml
AUTOSAR_VERSION ?= Autosar_4_0_2

.PHONY: help install install-dev generate generate-versioned merge update gui gui-versioned gui-flag gui-flag-versioned versioned-cli build-exe test

help:
	@echo Available targets:
	@echo   install                - Install runtime dependencies
	@echo   install-dev            - Install development dependencies
	@echo   generate               - Standard generation
	@echo   generate-versioned     - Versioned generation
	@echo   merge                  - Generate and merge with previous ARXML
	@echo   update                 - Update existing blocks with --allow-update
	@echo   gui                    - Launch the main GUI
	@echo   gui-versioned          - Launch the versioned GUI
	@echo   gui-flag               - Launch GUI using --gui flag
	@echo   gui-flag-versioned     - Launch versioned GUI using flags
	@echo   versioned-cli          - Flag-based versioned CLI generation
	@echo   build-exe              - Build the executable
	@echo   test                   - Run unit tests
	@echo.
	@echo Variables you can override:
	@echo   INPUT_TYPE=$(INPUT_TYPE)
	@echo   INPUT_FILE=$(INPUT_FILE)
	@echo   OUTPUT_DIR=$(OUTPUT_DIR)
	@echo   PREVIOUS_ARXML=$(PREVIOUS_ARXML)
	@echo   AUTOSAR_VERSION=$(AUTOSAR_VERSION)

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

generate:
	$(PYTHON) main.py generate --input-type $(INPUT_TYPE) --input-file $(INPUT_FILE) --output $(OUTPUT_DIR)

generate-versioned:
	$(PYTHON) main.py generate-versioned --input-type $(INPUT_TYPE) --input-file $(INPUT_FILE) --autosar-version $(AUTOSAR_VERSION) --output $(OUTPUT_DIR)

merge:
	$(PYTHON) main.py generate --input-type $(INPUT_TYPE) --input-file $(INPUT_FILE) --previous-arxml $(PREVIOUS_ARXML) --output $(OUTPUT_DIR)

update:
	$(PYTHON) main.py generate --input-type $(INPUT_TYPE) --input-file $(INPUT_FILE) --previous-arxml $(PREVIOUS_ARXML) --output $(OUTPUT_DIR) --allow-update

gui:
	$(PYTHON) main.py gui

gui-versioned:
	$(PYTHON) main.py gui-versioned

gui-flag:
	$(PYTHON) main.py --gui

gui-flag-versioned:
	$(PYTHON) main.py --gui --versioned

versioned-cli:
	$(PYTHON) main.py --versioned --input-type $(INPUT_TYPE) --input-file $(INPUT_FILE) --autosar-version $(AUTOSAR_VERSION)

build:
	$(POWERSHELL) -ExecutionPolicy Bypass -File .\build_exe.ps1

test:
	$(PYTHON) -m unittest discover -s tests -p "test_*.py"

clean:
	$(POWERSHELL) -NoProfile -Command "if (Test-Path 'release') { Remove-Item -Recurse -Force 'release' }"
	$(POWERSHELL) -NoProfile -Command "if (Test-Path 'dist') { Remove-Item -Recurse -Force 'dist' }"
	$(POWERSHELL) -NoProfile -Command "if (Test-Path '__pycache__') { Remove-Item -Recurse -Force '__pycache__' }"
	$(POWERSHELL) -NoProfile -Command "if (Test-Path 'NvMAutomationTool.spec') { Remove-Item -Recurse -Force 'NvMAutomationTool.spec' }"