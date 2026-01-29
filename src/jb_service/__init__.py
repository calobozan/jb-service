"""
jb-service: Python SDK for building jb-serve services.

Usage:
    from jb_service import Service, method, run
    
    class Calculator(Service):
        @method
        def add(self, a: float, b: float) -> float:
            return a + b
    
    if __name__ == "__main__":
        run(Calculator)
"""

from .service import Service
from .method import method
from .protocol import run

__version__ = "0.1.0"
__all__ = ["Service", "method", "run", "__version__"]
