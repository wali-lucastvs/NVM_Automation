# AUTOSAR NvM Automation Tool
This is new branch
Author : S M Wali Haider Zaidi

This workspace contains a Python-based generator for AUTOSAR NvM configuration artifacts:

- `NvM_Cfg.c`
- `NvM_Cfg.h`
- `NvM.arxml`

The tool reads NvM block definitions from JSON or Excel (`.xlsx` / `.xlsm`) and generates C and AUTOSAR ECUC-style ARXML output.

## Entry Point

Run the generator with:

```powershell
python generate_nvm.py samples/nvm_blocks.json --output output --verbose
```

Excel input is also supported:

```powershell
python generate_nvm.py samples/nvm_blocks.xlsx --output output
```

If you use Excel input, install:

```powershell
pip install -r requirements.txt
```

## JSON Input Format

The JSON file can be either:

- a top-level list of blocks, or
- an object with a `blocks` array

Required block fields:

- `block_name`
- `block_id`
- `block_size`
- `ram_block_name`
- `device` (`FEE` or `EA`)
- `block_management_type` (`NATIVE`, `REDUNDANT`, or `DATASET`)
- `use_crc` (`true` / `false`)
- `crc_type` (`CRC8`, `CRC16`, or `CRC32`)
- `write_protection` (`true` / `false`)

Optional fields supported by the generator for more AUTOSAR-like ARXML output:

- `device_id`
- `nv_block_base_number`
- `nv_block_num`

If the optional fields are not present:

- `device_id` defaults to `0` for `FEE` and `1` for `EA`
- `nv_block_base_number` defaults to `block_id`
- `nv_block_num` defaults to `1` for `NATIVE`, `2` for `REDUNDANT`, and `2` for `DATASET`

## Validation Rules

- `block_id` must be unique
- `block_size` must be greater than `0`
- `ram_block_name` must be a valid C identifier

The parser also warns if `block_id` is below `2`, because AUTOSAR typically reserves block IDs `0` and `1`.

## Notes

- The generated ARXML follows AUTOSAR ECUC-style `ECUC-MODULE-CONFIGURATION-VALUES` and `ECUC-CONTAINER-VALUE` layout for `NvMBlockDescriptor`.
- The input field `block_size` is mapped to the official AUTOSAR parameter `NvMNvBlockLength`.
- `NvMNvramDeviceId` is emitted as an integer parameter. When only `FEE` or `EA` is supplied, the generator uses default device IDs unless you override them in the input.
