# README
This is my attempt at the hiring challenge.

## Requirements
Please use python 3.12 or higher.

## Installation
Run the following command (preferably on a virtual environment):
```bash
pip install steel_plans_api-*.tar.gz
```

## Usage
With defaults:
```bash
steel-plans-api
```

Or with `uvicorn` at the root of the project:
```bash
uvicorn steel_plans_api:app
```

API docs:
```bash
http://<ip>:<port>/docs # e.g., http://127.0.0.1:8000/docs
http://<ip>:<port>/redoc # e.g., http://127.0.0.1:8000/redoc
```

### Run Tests
To run tests:
1. extract the package.
2. go to project root
3. Install with `[dev]`: `pip install .[dev]`
4. Run test in project root: `python -m pytest -q`

## Main Assumptions
Project Assumptions:
- database normalization can be conducted as a refinement step later on
- malformed data can be sent, so i use pydantic to validate the data
    - from examples, I expect a general convention/format
    - files uploaded will have the same general schema
- iterative development cycle
    - initial protype production forecast mechanism
    - due to lack of data, initial prototype for forecasting is relatively simple
    - if there was more data to work with, and more time, I could study it and improve on the current one

Deployabilty assumptions:
- has internet access
- is okay with installing a higher version python

## Main Features
- reasonable separation of concerns 
- runtime validation with pydantic
- pytests to make endpoints and pipeline services testable
- tests to validate invariants
- forecasting
    - forecast method is simple expontential smoothing to weigh more recent data more heavily.
    - hamilton rounding to distribute leftover proportions after normalizing them
