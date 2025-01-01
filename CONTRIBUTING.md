# Contributing to Project Radius

## Code Style
- C: C99 standard, `-Wall -Wextra` clean
- Python: PEP 8

## Branch Naming
- `feat/<name>` — new features
- `fix/<name>`  — bug fixes
- `docs/<name>` — documentation only

## Testing
```bash
cd src/c_engine && make test
source venv/bin/activate && python scripts/validate_calibration.py
```
