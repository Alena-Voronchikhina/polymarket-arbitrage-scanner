# Polymarket Project

A Python3 project for Polymarket analysis and tools.

## Setup

### Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Install dependencies
```bash
pip install -r requirements.txt
```

## Project Structure

```
.
├── src/              # Main application code
├── tests/            # Test files
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## Development

### Running tests
```bash
pytest
```

### Running with coverage
```bash
pytest --cov=src tests/
```

## License

MIT
