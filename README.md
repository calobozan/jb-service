# jb-service

Python SDK for building [jb-serve](https://github.com/calobozan/jb-serve) services.

## Installation

```bash
pip install jb-service
```

## Quick Start

```python
from jb_service import Service, method, run

class Calculator(Service):
    """A simple calculator service."""
    
    @method
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b
    
    @method
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

if __name__ == "__main__":
    run(Calculator)
```

That's it. Three imports, one decorator, and you have a working service.

## Features

- **Simple API**: Subclass `Service`, decorate methods with `@method`
- **Pydantic validation**: Type hints become JSON schema with automatic validation
- **Async support**: `async def` methods work out of the box
- **Logging**: `self.log` routes to jb-serve
- **Schema generation**: Auto-generate `jumpboot.yaml` from your code

## Usage with jb-serve

```bash
# Install your service
jb-serve install ./my-service

# Call methods
jb-serve call my-service.add a=1 b=2

# Or via HTTP
curl -X POST http://localhost:9800/v1/tools/my-service/add \
  -H "Content-Type: application/json" \
  -d '{"a": 1, "b": 2}'
```

## Documentation

See [PYTHON-SDK.md](https://github.com/calobozan/jb-serve/blob/main/docs/PYTHON-SDK.md) for full documentation.

## License

MIT
