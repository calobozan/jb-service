"""
jb-service: Python SDK for building jb-serve services.

Usage:
    from jb_service import Service, method, run
    from jb_service.types import FilePath, Audio, Image
    
    class Calculator(Service):
        @method
        def add(self, a: float, b: float) -> float:
            return a + b
    
    class AudioProcessor(Service):
        @method
        def process(self, audio: Audio) -> dict:
            sample_rate, data = audio  # Pre-loaded numpy array
            return {"sample_rate": sample_rate, "samples": len(data)}
    
    if __name__ == "__main__":
        run(Calculator)
"""

from .service import Service
from .method import method
from .protocol import run
from .types import FilePath, Audio, Image, save_image, save_audio

__version__ = "0.1.0"
__all__ = [
    "Service", "method", "run",
    "FilePath", "Audio", "Image",
    "save_image", "save_audio",
    "__version__"
]
