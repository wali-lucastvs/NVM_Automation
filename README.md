# AUTOSAR NvM Automation Tool

## Overview

This project generates AUTOSAR NvM artifacts from JSON or Excel input through a desktop GUI:

- `NvM_Cfg.c`
- `NvM_Cfg.h`
- `NvM.arxml`

The codebase now uses a desktop GUI as the only user-facing entry point, with a single generator module that supports both standard and versioned generation.

## Project Layout

```text
nvm_app/
  __init__.py
  gui.py

nvm_tool/
  __init__.py
  config.py
  generator.py
  models.py
  parser.py
  rules.py

tests/
  test_generator.py
  test_models.py
  test_parser.py
  test_versioned_generation.py

versions/
  common/
  Autosar_4_0_1/
    schema.xsd
    config.yaml
  ...

main.py
build_exe.ps1
requirements.txt
```

## Workspace

```text
workspace/
  input/
  output/
```

Generated files are written to `workspace/output` by default unless changed in the GUI. Packaged desktop builds are staged under `release/dist/`.

## Install

```powershell
pip install -r requirements.txt
```

## Usage

### Launch the GUI

```powershell
python -m nvm_app.gui
```

Within the GUI you can:

- Generate from JSON
- Generate from Excel
- Merge with a previous `NvM.arxml`
- Update an existing `NvM.arxml`
- Select an AUTOSAR version for versioned output

## Input fields

Required block fields:

- `block_name`
- `block_id`
- `block_size`
- `ram_block_name`
- `device`
- `block_management_type`
- `use_crc`
- `crc_type`
- `write_protection`

Optional fields:

- `device_id`
- `nv_block_base_number`
- `nv_block_num`

## Validation rules

- `block_id` must be unique and greater than `0`.
- `ram_block_name` must be a valid C identifier.
- `device` must be `FEE` or `EA`.
- `block_management_type` must be `NATIVE`, `REDUNDANT`, or `DATASET`.
- Dataset blocks must enable CRC.
- Merge mode rejects duplicate IDs and short names unless `--allow-update` is set.

## AUTOSAR versions

Available profiles are read from the directory names under `versions/`, for example:

- `Autosar_4_0_1`
- `Autosar_4_0_2`
- `Autosar_4_0_3`
- `Autosar_4_1_1`
- `Autosar_4_1_2`
- `Autosar_4_1_3`
- `Autosar_4_2_1`
- `Autosar_4_2_2`
- `Autosar_4_3_0`

## Build executable

```powershell
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

## Tests

```powershell
python -m unittest discover -s tests -p "test_*.py"
```
