# Installation

## Requirements

SmartSwitch requires Python 3.10 or higher.

## Install from PyPI

Once released, install SmartSwitch using pip:

```bash
pip install smartswitch
```

## Install from source

To install the latest development version:

```bash
git clone https://github.com/genropy/smartswitch.git
cd smartswitch
pip install -e .
```

## Development Installation

For development with all dependencies:

```bash
pip install -e ".[dev]"
```

This includes:
- pytest for testing
- black for code formatting
- ruff for linting
- coverage tools

## Verify Installation

Test your installation:

```python
from smartswitch import Switcher
print("SmartSwitch installed successfully!")
```

## Next Steps

Continue to the [Quick Start Guide](quickstart.md) to begin using SmartSwitch.
