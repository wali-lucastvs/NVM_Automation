# Makefile for NVM Automation Tool

.PHONY: all install install-dev build clean test run-gui run-generate help

# Default target
all: install install-dev test build

# Install production dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
install-dev:
	pip install -r requirements-dev.txt

# Build the executable
build:
	powershell -ExecutionPolicy Bypass -File build_exe.ps1

# Clean build artifacts
clean:
	powershell -ExecutionPolicy Bypass -File build_exe.ps1 -Clean

# Run tests
test:
	python -m unittest discover tests

# Run the GUI application
run-gui:
	python nvm_gui.py

# Run the NVM generator
run-generate:
	python generate_nvm.py

# Show help
help:
	@echo "Available targets:"
	@echo "  all          - Install dependencies, run tests, and build"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  build        - Build the executable using PyInstaller"
	@echo "  clean        - Clean build artifacts"
	@echo "  test         - Run unit tests"
	@echo "  run-gui      - Run the GUI application"
	@echo "  run-generate - Run the NVM generator script"
	@echo "  help         - Show this help message"