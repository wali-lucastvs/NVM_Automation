# Test Organization

Each test case ID is embedded in the test method name so it appears in standard
`unittest` output and can be referenced from bug reports, reviews, or traceability
matrices.

## Test Case ID Prefixes

- `MODEL_REQ`: generation request normalization and validation.
- `MODEL_INPUT`: input type detection.
- `MODEL_BLOCK`: NvM block model defaults.
- `MODEL_MEMORY`: memory usage summaries.
- `WORKSPACE`: workspace path behavior.
- `PARSER_JSON`: JSON input parsing.
- `PARSER_ARXML`: previous ARXML parsing.
- `GEN_ARTIFACT`: generated file creation and artifact content.
- `GEN_MERGE`: ARXML merge behavior.
- `VERSION_PROFILE`: AUTOSAR version profile loading.
- `VERSION_GEN`: versioned AUTOSAR generation.
- `VALIDATION`: business rule and invalid input validation.

Run all tests with:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```
