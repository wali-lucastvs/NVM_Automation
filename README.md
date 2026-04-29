# AUTOSAR NvM Automation Tool

## Overview

This project generates AUTOSAR NvM artifacts from JSON or Excel input:

- `NvM_Cfg.c`
- `NvM_Cfg.h`
- `NvM.arxml`

The codebase now uses a unified entry point, merged model/config modules, and a single generator module that supports both standard and versioned generation.

## Project Layout

```text
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
requirements-dev.txt
```

## Workspace

```text
workspace/
  input/
  output/
```

Generated files are written to `workspace/output` by default.

## Install

```powershell
pip install -r requirements.txt
```

## Usage

### Standard generation

```powershell
python main.py generate --input-type json --input-file workspace/input/nvm_blocks.json --output workspace/output
```

### Versioned generation

```powershell
python main.py generate-versioned --input-type json --input-file workspace/input/nvm_blocks.json --autosar-version Autosar_4_0_2 --output workspace/output
```

### Merge with a previous ARXML

```powershell
python main.py generate --input-type json --input-file workspace/input/nvm_blocks.json --previous-arxml workspace/input/NvM.arxml --output workspace/output
```

### Update existing blocks

```powershell
python main.py generate --input-type json --input-file workspace/input/nvm_blocks.json --previous-arxml workspace/input/NvM.arxml --output workspace/output --allow-update
```

### Launch the main GUI

```powershell
python main.py gui
```

### Launch the versioned GUI

```powershell
python main.py gui-versioned
```

### Flag-based entry

```powershell
python main.py --gui
python main.py --gui --versioned
python main.py --versioned --input-type json --input-file workspace/input/nvm_blocks.json --autosar-version Autosar_4_0_2
```

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
pip install -r requirements-dev.txt
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

## Tests

```powershell
python -m unittest discover -s tests -p "test_*.py"
```
