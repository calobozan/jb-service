# jb-service

Python SDK for building [jb-serve](https://github.com/calobozan/jb-serve) tools.

## Installation

```bash
pip install git+https://github.com/calobozan/jb-service.git
```

## Quick Start

```python
from jb_service import Service, method, run

class Calculator(Service):
    @method
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

if __name__ == "__main__":
    run(Calculator)
```

That's it. Three imports, one decorator, and you have a working tool.

## Features

- **Simple API**: Subclass `Service`, decorate methods with `@method`
- **Two transports**: REPL (simple) or MessagePack (stdout-safe)
- **File types**: `FilePath`, `Audio`, `Image` for automatic file handling
- **Pydantic validation**: Type hints become JSON schema
- **Async support**: `async def` methods work out of the box
- **Logging**: `self.log` routes to jb-serve

## Two Service Types

### Service (REPL transport)
For simple tools where stdout isn't used for other purposes.

```python
from jb_service import Service, method, run

class Calculator(Service):
    @method
    def add(self, a: float, b: float) -> float:
        return a + b

if __name__ == "__main__":
    run(Calculator)
```

### MessagePackService (MessagePack transport)
For tools with progress bars, tqdm, or anything that writes to stdout.

```python
from jb_service import MessagePackService, method, run, save_image

class ImageGenerator(MessagePackService):
    def setup(self):
        from diffusers import SomePipeline
        # Progress bars during model loading are fine!
        self.pipe = SomePipeline.from_pretrained("model-name")
    
    @method
    def generate(self, prompt: str) -> dict:
        # tqdm progress bars during generation are fine!
        result = self.pipe(prompt)
        path = save_image(result.images[0])
        return {"image": path}

if __name__ == "__main__":
    run(ImageGenerator)  # Auto-detects MessagePackService
```

**Manifest:**
```yaml
runtime:
  transport: msgpack  # Required for MessagePackService
```

## Lifecycle Methods

```python
class MyTool(Service):
    def setup(self):
        """Called once on startup. Load models, initialize state."""
        self.model = load_model()
    
    def teardown(self):
        """Called on shutdown. Cleanup resources."""
        self.model.unload()
    
    # Async versions also supported:
    async def setup_async(self):
        ...
    
    async def teardown_async(self):
        ...
```

## File Handling

### Input Types

```python
from jb_service import Service, method, FilePath, Audio, Image

class MediaProcessor(Service):
    @method
    def process_path(self, file: FilePath) -> dict:
        # file = "/path/to/file" (string)
        # Use when your library handles file loading
        ...
    
    @method
    def process_audio(self, audio: Audio) -> dict:
        # audio = (sample_rate, numpy_array)
        # Pre-loaded by jb-service
        sample_rate, data = audio
        ...
    
    @method
    def process_image(self, image: Image) -> dict:
        # image = PIL.Image
        # Pre-loaded by jb-service
        width, height = image.size
        ...
```

### Output Files

Use `save_image()` or return paths directly:

```python
from jb_service import MessagePackService, method, run, save_image

class Generator(MessagePackService):
    @method
    def generate(self, prompt: str) -> dict:
        image = self.pipe(prompt).images[0]
        
        # save_image handles temp file creation
        path = save_image(image, format="png")
        
        return {"image": path}  # jb-serve wraps as FileRef
```

**Response:**
```json
{
  "image": {
    "ref": "43af6f50",
    "url": "/v1/files/43af6f50.png",
    "size": 1211477,
    "media_type": "image/png"
  }
}
```

## Logging

```python
class MyTool(Service):
    @method
    def process(self, data: str) -> dict:
        self.log.info("Processing started")
        self.log.debug(f"Input: {data}")
        # ...
        self.log.info("Done")
        return {"result": "..."}
```

## Async Methods

```python
class AsyncTool(Service):
    @method
    async def fetch_data(self, url: str) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return {"data": await resp.text()}
```

## Usage with jb-serve

```bash
# Install your tool
jb-serve install ./my-tool

# Call methods
jb-serve call my-tool.add a=1 b=2

# Or via HTTP
curl -X POST http://localhost:9800/v1/tools/my-tool/add \
  -H "Content-Type: application/json" \
  -d '{"a": 1, "b": 2}'
```

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `Service` | Base class for REPL transport tools |
| `MessagePackService` | Base class for MessagePack transport tools |

### Decorators

| Decorator | Description |
|-----------|-------------|
| `@method` | Expose a method as an RPC endpoint |

### Functions

| Function | Description |
|----------|-------------|
| `run(ServiceClass)` | Start the service (auto-detects transport) |
| `save_image(img, format="png")` | Save PIL Image, return path |

### Types

| Type | Description |
|------|-------------|
| `FilePath` | Pass file path as string |
| `Audio` | Load audio as `(sample_rate, ndarray)` |
| `Image` | Load image as `PIL.Image` |

## License

MIT
