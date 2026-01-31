"""
jb-service: Python SDK for building jb-serve services.

Usage:
    from jb_service import Service, method, run
    from jb_service.types import FilePath, Audio, Image
    
    # Simple service (REPL transport - no stdout allowed)
    class Calculator(Service):
        @method
        def add(self, a: float, b: float) -> float:
            return a + b
    
    # Complex service with stdout (MessagePack transport)
    from jb_service import MessagePackService
    
    class ImageGenerator(MessagePackService):
        @method
        def generate(self, prompt: str) -> dict:
            # Progress bars, logging, etc. are fine
            result = self.pipeline(prompt)
            return {"image": save_image(result)}
    
    if __name__ == "__main__":
        run(Calculator)  # or run(ImageGenerator)

File Store:
    # Tools can use self.files for persistent file storage
    class MyTool(Service):
        @method
        def process(self, input: str) -> dict:
            output_path = self.do_work(input)
            
            # Import into store with 1 hour TTL
            file_id = self.files.import_file(output_path, ttl=3600)
            
            return {"file_id": file_id}
"""

from .service import Service
from .msgpack_service import MessagePackService
from .method import method
from .protocol import run
from .types import FilePath, Audio, Image, save_image, save_audio
from .filestore import FileStore, FileInfo, FileStoreError, get_filestore

__version__ = "0.1.0"
__all__ = [
    "Service", "MessagePackService", "method", "run",
    "FilePath", "Audio", "Image",
    "save_image", "save_audio",
    "FileStore", "FileInfo", "FileStoreError", "get_filestore",
    "__version__"
]
