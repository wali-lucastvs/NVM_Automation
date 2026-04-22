# AUTOSAR NvM Automation Tool

**Author and Owner:** S M Wali Haider Zaidi

## Overview

This Python-based automation tool generates AUTOSAR NvM (Non-Volatile Memory) configuration artifacts from JSON or Excel input files. It reads NvM block definitions and produces:

- `NvM_Cfg.c` - C source file with configuration
- `NvM_Cfg.h` - C header file
- `NvM.arxml` - AUTOSAR ECUC-style XML configuration

The tool supports merging new blocks with previously generated ARXML files, input validation, CRC configuration, and comprehensive error checking.

---

## Installation & Requirements

### Prerequisites

- Python 3.8+
- Required dependency for Excel support: `openpyxl>=3.1.0`

### Setup

```powershell
# Install dependencies (required for Excel input)
pip install -r requirements.txt
```

---

## Quick Start

### Basic JSON Input (Generate NvM Configuration)

```powershell
python generate_nvm.py --input-type json --input-file input/nvm_blocks.json --output output
```

### Basic Excel Input

```powershell
python generate_nvm.py --input-type excel --input-file input/NVM_Data.xlsx --output output
```

---

## All Available Commands

### 1. Generate from JSON (Basic)

Generate NvM configuration files from a JSON input file:

```powershell
python generate_nvm.py --input-type json --input-file input/nvm_blocks.json --output output
```

```powershell
python generate_nvm.py --input-type json --input-file input/nvm_blocks.json --output output --verbose
```

**Output:** Generates `NvM_Cfg.c`, `NvM_Cfg.h`, and `NvM.arxml` in the output directory.

---


### 2. Generate from Excel (XLSX/XLSM)

```powershell
python generate_nvm.py --input-type excel --input-file input/NVM_Data.xlsx --output output
```

```powershell
python generate_nvm.py --input-type excel --input-file input/NVM_Data.xlsx --output output --verbose
```


**Purpose:** Reads NvM block definitions from an Excel spreadsheet instead of JSON.

---

### 3. Merge New Blocks with Previous ARXML (JSON Input)

Append new blocks to an existing `NvM.arxml` file while preserving previous block configurations:

```powershell
python generate_nvm.py --input-type json --input-file input/nvm_blocks.json --previous-arxml input/NvM.arxml --output output
```

```powershell
python generate_nvm.py --input-type json --input-file input/nvm_blocks.json --previous-arxml input/NvM.arxml --output output --verbose
```

**Purpose:** Merges new block definitions with an already-generated ARXML, keeping all existing blocks intact and appending new ones.

---

### 4. Merge New Blocks with Previous ARXML (Excel Input)

```powershell
python generate_nvm.py --input-type excel --input-file input/NVM_Data.xlsx --previous-arxml input/NvM.arxml --output output
```

```powershell
python generate_nvm.py --input-type excel --input-file input/NVM_Data.xlsx --previous-arxml input/NvM.arxml --output output --verbose
```


---

### 5. Update Existing Blocks (JSON Input with --allow-update)

Modify existing blocks in a previous ARXML by providing new block data with the same block ID:

```powershell
python generate_nvm.py --input-type json --input-file input/nvm_blocks.json --previous-arxml input/NvM.arxml --output output --allow-update
```

```powershell
python generate_nvm.py --input-type json --input-file input/nvm_blocks.json --previous-arxml input/NvM.arxml --output output --allow-update --verbose
```

**Purpose:** Replaces existing blocks (matching by ID) with updated configurations instead of rejecting them.

---

### 6. Update Existing Blocks (Excel Input with --allow-update)

```powershell
python generate_nvm.py --input-type excel --input-file input/NVM_Data.xlsx --previous-arxml input/NvM.arxml --output output --allow-update
```

```powershell
python generate_nvm.py --input-type excel --input-file input/NVM_Data.xlsx --previous-arxml input/NvM.arxml --output output --allow-update --verbose
```

---



### 7. Specify Custom Output Directory

All commands accept `--output` to customize where files are written (default: `output` folder):

```powershell
python generate_nvm.py --input-type json --input-file input/nvm_blocks.json --output C:\CustomPath\nvm_output
```

---

### 8. Display Help

```powershell
python generate_nvm.py --help
```

Shows all available arguments and their descriptions.


---

## Input Format Specifications

### JSON Input Format

The JSON file must contain NvM block definitions in one of two structures:

#### Structure 1: Top-level Array

```json
[
  {
    "block_name": "BlockA",
    "block_id": 5,
    "block_size": 256,
    "ram_block_name": "Ram_BlockA",
    "device": "FEE",
    "block_management_type": "NATIVE",
    "use_crc": true,
    "crc_type": "CRC16",
    "write_protection": false
  }
]
```

#### Structure 2: Object with `blocks` Array

```json
{
  "blocks": [
    {
      "block_name": "BlockA",
      "block_id": 5,
      "block_size": 256,
      "ram_block_name": "Ram_BlockA",
      "device": "FEE",
      "block_management_type": "NATIVE",
      "use_crc": true,
      "crc_type": "CRC16",
      "write_protection": false
    }
  ]
}
```

### Required JSON Fields

| Field | Type | Description | Valid Values |
|-------|------|-------------|---------------|
| `block_name` | string | Unique identifier for the block | Any non-empty string |
| `block_id` | integer | Unique numeric block identifier | Integer > 0 (note: 0 & 1 reserved by AUTOSAR) |
| `block_size` | integer | Size of the NV block in bytes | Integer > 0 |
| `ram_block_name` | string | C RAM block variable name | Valid C identifier |
| `device` | string | Storage device type | `FEE` or `EA` |
| `block_management_type` | string | Block management strategy | `NATIVE`, `REDUNDANT`, or `DATASET` |
| `use_crc` | boolean | Enable CRC protection | `true` or `false` |
| `crc_type` | string | CRC algorithm type | `CRC8`, `CRC16`, or `CRC32` |
| `write_protection` | boolean | Enable write protection | `true` or `false` |

### Optional JSON Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `device_id` | integer | `0` for FEE, `1` for EA | AUTOSAR device identifier |
| `nv_block_base_number` | integer | Same as `block_id` | Base block number for AUTOSAR |
| `nv_block_num` | integer | `1` for NATIVE, `2` for REDUNDANT/DATASET | Number of NV blocks |

**Note:** If optional fields are not provided, the generator uses sensible defaults based on device type and management type.

---

### Excel Input Format

The Excel file (`.xlsx` or `.xlsm`) should contain a sheet with columns matching the JSON field names:

| Column Name | Type | Required |
|-------------|------|----------|
| block_name | text | Yes |
| block_id | number | Yes |
| block_size | number | Yes |
| ram_block_name | text | Yes |
| device | text | Yes |
| block_management_type | text | Yes |
| use_crc | boolean/text | Yes |
| crc_type | text | Yes |
| write_protection | boolean/text | Yes |
| device_id | number | No |
| nv_block_base_number | number | No |
| nv_block_num | number | No |

**Example Sheet Layout:**

```
block_name | block_id | block_size | ram_block_name | device | block_management_type | use_crc | crc_type | write_protection
-----------|----------|------------|----------------|---------|-----------------------|---------|----------|------------------
BlockA     | 5        | 256        | Ram_BlockA     | FEE     | NATIVE                | TRUE    | CRC16    | FALSE
BlockB     | 10       | 512        | Ram_BlockB     | EA      | REDUNDANT             | TRUE    | CRC32    | TRUE
```

---

## Validation Rules & Constraints

### Block ID Rules

- ✓ `block_id` must be **unique** across all blocks
- ✓ `block_id` must be greater than **0**
- ⚠️ **WARNING:** Block IDs below `2` are discouraged (AUTOSAR reserves `0` and `1` for special purposes)
- ✓ Must be an integer

### Block Size Rules

- ✓ `block_size` must be **greater than 0**
- ✓ Should be reasonable for target hardware (typically 1 to 65536 bytes)
- ✓ Must be an integer

### Name Rules

- ✓ `ram_block_name` must be a **valid C identifier**
  - Starts with letter or underscore
  - Contains only letters, digits, and underscores
  - Examples: `Ram_Block_1`, `_internal_data`, `CONFIG_DATA`
  
- ✓ `block_name` cannot be empty
- ✓ Special characters in block names are sanitized and converted to underscores

### Device Configuration Rules

- ✓ `device` must be either `FEE` (Flash) or `EA` (EEPROM)
- ✓ `device_id` is auto-assigned (0 for FEE, 1 for EA) if not specified
- ✓ Custom `device_id` can be provided for multiple devices

### Block Management Type Rules

- ✓ Must be one of: `NATIVE`, `REDUNDANT`, or `DATASET`
  - `NATIVE`: Single block, no redundancy
  - `REDUNDANT`: Dual blocks for fault tolerance
  - `DATASET`: Multiple dataset blocks
- ✓ Affects default `nv_block_num` if not specified

### CRC & Protection Rules

- ✓ `use_crc` must be `true` or `false`
- ✓ If `use_crc` is `true`, `crc_type` must be specified: `CRC8`, `CRC16`, or `CRC32`
- ✓ `write_protection` must be `true` or `false`

### Merge Validation Rules (when using `--previous-arxml`)

- ✓ No duplicate `SHORT-NAME` values allowed between previous and new blocks (unless `--allow-update` is used)
- ✓ No duplicate `NvMNvramBlockIdentifier` values allowed between previous and new blocks (unless `--allow-update` is used)
- ✓ All previous blocks are preserved in exact order
- ✓ New blocks are appended after previous blocks

### Block Update Mode (`--allow-update` flag)

When using `--allow-update` with `--previous-arxml`:

- ✓ Blocks with matching IDs are **replaced** with the new definition
- ✓ Blocks are replaced in-place (order preserved)
- ✓ Blocks without a match in previous ARXML are **appended**
- ✓ Useful for modifying existing block configurations without manual deletion

**Example:**
```powershell
# Update existing block with ID 10, append new block with ID 20
python generate_nvm.py --input-type excel --input-file input/updates.xlsx --previous-arxml output/NvM.arxml --output output --allow-update
```

---

## Important Notes

### AUTOSAR Compliance

- The generated ARXML follows **AUTOSAR ECUC-style** configuration format:
  - Uses `ECUC-MODULE-CONFIGURATION-VALUES` for the NvM module
  - Uses `ECUC-CONTAINER-VALUE` for individual `NvMBlockDescriptor` entries
  - Complies with AUTOSAR XSD schema namespace: `http://autosar.org/schema/r4.0`

### Block Size Mapping

- The input field `block_size` is mapped to the AUTOSAR parameter **`NvMNvBlockLength`** in the generated ARXML

### Device ID Configuration

- `NvMNvramDeviceId` is emitted as an integer parameter in the ARXML
- For single-device configurations (only FEE or only EA), default device IDs are used:
  - FEE: `device_id = 0`
  - EA: `device_id = 1`
- Override defaults by specifying custom `device_id` values in input

### ARXML Merge Behavior

When using `--previous-arxml` flag:

1. **Preservation:** All existing `NvMBlockDescriptor` containers from the previous ARXML are copied first
2. **Appending:** Newly generated blocks are appended after the previous blocks
3. **Duplicate Detection:** The generator validates and rejects:
   - Duplicate block names (SHORT-NAME)
   - Duplicate block IDs (NvMNvramBlockIdentifier)
4. **Order:** Previous blocks maintain their original order, new blocks follow in declaration order

### Generated Files

| File | Purpose |
|------|---------|
| `NvM_Cfg.h` | C header with block definitions and AUTOSAR configuration |
| `NvM_Cfg.c` | C source with initialization and helper functions |
| `NvM.arxml` | AUTOSAR ECUC XML configuration (merged if `--previous-arxml` provided) |

### Logging Levels

- **Without `--verbose`:** Shows `INFO` level logs (errors and important steps)
- **With `--verbose`:** Shows `DEBUG` level logs (detailed parsing, validation, and generation steps)

---

## Error Handling

The tool provides detailed error messages for common issues:

- **Missing required fields** in input
- **Invalid field values** (e.g., invalid device, invalid CRC type)
- **Validation failures** (e.g., duplicate block IDs, invalid C identifiers)
- **File not found** errors (input or previous ARXML)
- **Merge conflicts** (duplicate names or IDs during merge)

All errors are logged with context to help identify and fix issues in the input.

---

## Example Workflows

### Workflow 1: Initial Configuration from JSON

```powershell
python generate_nvm.py --input-type json --input-file input/nvm_blocks.json --output output --verbose
```

### Workflow 2: Add New Blocks to Existing Configuration

```powershell
# Previous run generated: output/NvM.arxml
# New blocks in: input/new_blocks.json

python generate_nvm.py --input-type json --input-file input/new_blocks.json --previous-arxml output/NvM.arxml --output output --verbose
```

### Workflow 3: Generate from Excel with Custom Output Path

```powershell
python generate_nvm.py --input-type excel --input-file input/NVM_Data.xlsx --output "C:\Projects\NvM_Config" --verbose
```

### Workflow 4: Update Existing Blocks in Previous Configuration

```powershell
# Modify block properties in input file (same block ID)
# Run with --allow-update to replace the old block

python generate_nvm.py --input-type excel --input-file input/NVM_Data_Updated.xlsx --previous-arxml output/NvM.arxml --output output --allow-update --verbose
```

This will replace blocks with matching IDs while keeping other blocks intact.

---

### Workflow 5: Batch Processing Multiple Configurations

```powershell
# Process Configuration A
python generate_nvm.py --input-type json --input-file input/config_a.json --output output\config_a

# Process Configuration B (merging with existing)
python generate_nvm.py --input-type json --input-file input/config_b.json --previous-arxml output\config_a\NvM.arxml --output output\config_ab
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Excel file not recognized** | Ensure `openpyxl` is installed: `pip install -r requirements.txt` |
| **Duplicate block ID error** | Either use `--allow-update` to modify the block, or remove duplicate from input |
| **Duplicate block name error** | Either use `--allow-update` to modify the block, or use different name in input |
| **Invalid C identifier error** | `ram_block_name` must start with letter/underscore and contain only alphanumeric/underscore |
| **Reserved block ID warning** | Block IDs 0 and 1 are reserved by AUTOSAR; use IDs ≥ 2 |
| **File not found** | Verify file paths are correct and files exist |
| **Merge validation failed** | Check for duplicate block names or IDs between new input and previous ARXML |

---

## Scope of Improvement
ARXML Schema Validation
GUI addition
Expantion of this use case for FEE , Flash and MemIf

---

## Support & Contribution

For issues, feature requests, or questions, please contact the tool author.

**Author:** S M Wali Haider Zaidi