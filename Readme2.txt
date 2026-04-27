GUI Created :
GUI Build Command : powershell -ExecutionPolicy Bypass -File .\build_exe.ps1 -Clean

# NVM Automation Tool - Future Editing Guide

## Overview
This project is an AUTOSAR NvM (Non-Volatile Memory) automation tool that generates configuration artifacts from input data. The "database" refers to the input data structures (JSON/Excel files containing NvM block definitions) and the generated outputs (C files, headers, ARXML).

## Project Structure
- `nvm_gui.py`: Main GUI application
- `generate_nvm.py`: CLI entry point
- `nvm_tool/`: Core modules
  - `application.py`: Argument parsing and main logic
  - `parser.py`: Input file parsing (JSON/Excel)
  - `models.py`: Data models for NvM blocks
  - `generator.py`: Output file generation
- `input/`: Sample input files
- `output/`: Generated files
- `tests/`: Unit tests
- `build_exe.ps1`: Build script for .exe
- `requirements.txt`: Runtime dependencies
- `requirements-dev.txt`: Development dependencies

## Editing Input Data (Database)
The "database" is the NvM block definitions in JSON or Excel format.

### JSON Input Structure
Located in `input/nvm_blocks.json`. Structure:
```json
{
  "blocks": [
    {
      "id": 1,
      "name": "Block1",
      "size": 100,
      "crc": "CRC16",
      "default_data": [0, 1, 2, ...],
      "nvram_block_identifier": "NvM_Block_1"
    }
  ]
}
```
- `id`: Unique block ID (integer)
- `name`: Block name (string)
- `size`: Block size in bytes (integer)
- `crc`: CRC type ("CRC8", "CRC16", "CRC32", or null)
- `default_data`: Array of default values (integers 0-255)
- `nvram_block_identifier`: AUTOSAR identifier (string)


***NOTE***
          "NATIVE"	  -> 1 copy   -> 	Single block, no redundancy
          "REDUNDANT"	-> 2 copies ->	Dual blocks for fault tolerance
          "DATASET"	  -> 2 copies ->	Multiple dataset block

### Excel Input Structure
Located in `input/NVM_Data.xlsx`. Columns:
- ID: Block ID
- Name: Block name
- Size: Block size
- CRC: CRC type
- Default Data: Comma-separated hex values (e.g., "0x00,0x01,0x02")
- NVRAM Block Identifier: AUTOSAR identifier

### Editing Steps
1. Open the JSON file in a text editor or Excel file in Excel
2. Modify block definitions as needed
3. Validate the structure (see tests)
4. Run generation to test changes

## Editing Code
### Prerequisites
- Python 3.8+
- Install dependencies: `pip install -r requirements-dev.txt`

### Code Modules
- **application.py**: Modify argument parsing or generation logic
- **parser.py**: Update input parsing for new formats or fields
- **models.py**: Change data models for NvM blocks
- **generator.py**: Alter output file generation (C code, ARXML)
- **nvm_gui.py**: Update GUI layout, buttons, or functionality

### Development Workflow
1. Make changes to Python files
2. Run tests: `python -m pytest tests/`
3. Test GUI: `python nvm_gui.py`
4. Build .exe: `powershell -ExecutionPolicy Bypass -File .\build_exe.ps1 -Clean`

## Build Process
### Building .exe
1. Ensure PyInstaller is installed: `pip install -r requirements-dev.txt`
2. Run build script: `powershell -ExecutionPolicy Bypass -File .\build_exe.ps1 -Clean`
3. Output: `dist/NvMAutomationTool.exe`

### Clean Build
- Removes old artifacts before building
- Use `-Clean` flag for fresh builds

## Dependencies
### Runtime
- openpyxl: Excel file handling
- lxml: XML processing
- tkinter: GUI (built-in with Python)

### Development
- PyInstaller: .exe building
- pytest: Testing
- Additional tools in requirements-dev.txt

## Testing
Run tests with: `python -m pytest tests/`
- Tests cover parsing, generation, and GUI
- Add new tests for modified code

## Version Control
- Use Git for changes
- Commit input files, code changes, and build outputs
- Tag releases for .exe versions

## Troubleshooting
- If .exe shows old version: Close running instances, rebuild with -Clean
- Import errors: Check Python path and dependencies
- Parsing errors: Validate input file structure
- Build fails: Check PyInstaller installation and Python version

## Future Enhancements
- Add new input formats
- Extend GUI features
- Improve error handling
- Add configuration validation

Last Updated: April 24, 2026
