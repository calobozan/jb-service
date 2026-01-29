"""
Service base class for jb-serve services.
"""
import logging
import sys
import json
from typing import Any


class ServiceLogger:
    """
    Logger that routes to jb-serve via stdout protocol.
    """
    
    def __init__(self, name: str):
        self.name = name
        self._enabled = True
    
    def _emit(self, level: str, message: str, extra: dict | None = None):
        """Emit a log message via the jb protocol."""
        if not self._enabled:
            return
        
        log_msg = {
            "log": {
                "level": level,
                "message": message,
                "name": self.name,
            }
        }
        if extra:
            log_msg["log"]["extra"] = extra
        
        # Write to stderr to avoid mixing with protocol messages on stdout
        print(json.dumps(log_msg), file=sys.stderr, flush=True)
    
    def debug(self, message: str, extra: dict | None = None):
        self._emit("debug", message, extra)
    
    def info(self, message: str, extra: dict | None = None):
        self._emit("info", message, extra)
    
    def warning(self, message: str, extra: dict | None = None):
        self._emit("warning", message, extra)
    
    def error(self, message: str, extra: dict | None = None):
        self._emit("error", message, extra)
    
    def critical(self, message: str, extra: dict | None = None):
        self._emit("critical", message, extra)


class Service:
    """
    Base class for jb-serve services.
    
    Subclass this and decorate methods with @method to create RPC endpoints.
    
    Example:
        from jb_service import Service, method
        
        class Calculator(Service):
            @method
            def add(self, a: float, b: float) -> float:
                return a + b
    """
    
    # Override in subclass for custom metadata
    name: str = None  # Defaults to class name lowercase
    version: str = "0.0.0"
    
    def __init__(self):
        from .method import is_method
        
        # Set default name from class name
        if self.name is None:
            self.name = self.__class__.__name__.lower()
        
        # Initialize logger
        self.log = ServiceLogger(self.name)
        
        # Discover @method decorated methods
        self._methods: dict[str, Any] = {}
        for attr_name in dir(self):
            if attr_name.startswith('_'):
                continue
            attr = getattr(self, attr_name)
            if is_method(attr):
                self._methods[attr_name] = attr
    
    def setup(self):
        """
        Called once when the service starts.
        
        Override to load models, initialize connections, etc.
        """
        pass
    
    async def setup_async(self):
        """
        Async version of setup. Called if defined.
        """
        pass
    
    def teardown(self):
        """
        Called when the service stops.
        
        Override to cleanup resources.
        """
        pass
    
    async def teardown_async(self):
        """
        Async version of teardown. Called if defined.
        """
        pass
    
    def _get_method(self, name: str):
        """Get a method by name."""
        if name not in self._methods:
            raise AttributeError(f"Unknown method: {name}")
        return self._methods[name]
    
    def _list_methods(self) -> list[str]:
        """List available method names."""
        return list(self._methods.keys())
