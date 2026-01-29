"""
Jumpboot communication protocol.

Handles the REPL-based communication between jb-serve (Go) and the Python service.
"""
import asyncio
import inspect
import json
import sys
import traceback
from typing import Any, Type

from pydantic import BaseModel, ValidationError, create_model
from pydantic.fields import FieldInfo

from .service import Service
from .method import is_method, is_async_method
from .schema import service_to_schema, method_to_schema


def build_pydantic_model(method_func) -> Type[BaseModel] | None:
    """
    Build a Pydantic model for validating method inputs.
    
    Returns None if the method has no parameters (other than self).
    """
    fn = getattr(method_func, '_jb_original', method_func)
    sig = inspect.signature(fn)
    
    try:
        hints = get_type_hints_safe(fn)
    except Exception:
        hints = {}
    
    fields = {}
    for param_name, param in sig.parameters.items():
        if param_name == 'self':
            continue
        
        # Get type annotation or default to Any
        annotation = hints.get(param_name, Any)
        
        # Handle default value
        if param.default is inspect.Parameter.empty:
            fields[param_name] = (annotation, ...)
        else:
            fields[param_name] = (annotation, param.default)
    
    if not fields:
        return None
    
    return create_model(f'{fn.__name__}_Input', **fields)


def get_type_hints_safe(fn):
    """Get type hints, handling forward references gracefully."""
    from typing import get_type_hints
    try:
        return get_type_hints(fn)
    except Exception:
        # Fall back to __annotations__ without resolving
        return getattr(fn, '__annotations__', {})


class Protocol:
    """
    Handles the jb-serve ↔ Python communication protocol.
    """
    
    def __init__(self, service: Service):
        self.service = service
        self._input_models: dict[str, Type[BaseModel] | None] = {}
        
        # Pre-build input models for all methods
        for name, method in service._methods.items():
            self._input_models[name] = build_pydantic_model(method)
    
    def _validate_params(self, method_name: str, params: dict) -> dict:
        """Validate and coerce input parameters using Pydantic."""
        model = self._input_models.get(method_name)
        if model is None:
            return params
        
        try:
            validated = model(**params)
            return validated.model_dump()
        except ValidationError as e:
            raise ValueError(f"Invalid parameters: {e}")
    
    async def handle_call(self, method_name: str, params: dict) -> dict:
        """
        Handle an RPC call.
        
        Returns a response dict with ok, result/error, and done fields.
        """
        try:
            # Get the method
            method = self.service._get_method(method_name)
            
            # Validate parameters
            validated_params = self._validate_params(method_name, params)
            
            # Call the method
            if is_async_method(method):
                result = await method(**validated_params)
            else:
                result = method(**validated_params)
            
            return {"ok": True, "result": result, "done": True}
        
        except Exception as e:
            return {
                "ok": False,
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                },
                "done": True,
            }
    
    def handle_schema(self) -> dict:
        """Return the service schema."""
        return service_to_schema(self.service.__class__)
    
    def handle_method_schema(self, method_name: str) -> dict:
        """Return schema for a specific method."""
        method = self.service._get_method(method_name)
        return method_to_schema(method)


async def run_async(service_class: Type[Service]):
    """
    Run the service with async support.
    
    This is the main entry point that handles:
    1. Service instantiation and setup
    2. Registering globals for jumpboot REPL
    3. Handling RPC calls
    4. Cleanup on exit
    """
    # Instantiate service
    service = service_class()
    protocol = Protocol(service)
    
    # Call setup
    service.log.debug("Running setup...")
    if asyncio.iscoroutinefunction(service.setup_async):
        # Check if it's been overridden
        if service.setup_async.__func__ is not Service.setup_async:
            await service.setup_async()
        else:
            service.setup()
    else:
        service.setup()
    service.log.debug("Setup complete")
    
    # Create the __jb_call__ handler
    loop = asyncio.get_event_loop()
    
    def __jb_call__(method: str, params: dict = None) -> dict:
        """Synchronous wrapper for async call handler."""
        if params is None:
            params = {}
        
        # Run the async handler in the event loop
        future = asyncio.run_coroutine_threadsafe(
            protocol.handle_call(method, params),
            loop
        )
        return future.result()
    
    def __jb_schema__() -> dict:
        """Return service schema."""
        return protocol.handle_schema()
    
    def __jb_method_schema__(method_name: str) -> dict:
        """Return method schema."""
        return protocol.handle_method_schema(method_name)
    
    def __jb_methods__() -> list[str]:
        """List available methods."""
        return service._list_methods()
    
    # Register globals for jumpboot REPL
    import builtins
    builtins.__jb_call__ = __jb_call__
    builtins.__jb_schema__ = __jb_schema__
    builtins.__jb_method_schema__ = __jb_method_schema__
    builtins.__jb_methods__ = __jb_methods__
    
    # Signal ready
    print("__JB_READY__", flush=True)
    service.log.info(f"Service {service.name} ready")
    
    try:
        # Keep the event loop running
        # The jumpboot REPL will call our globals directly
        while True:
            await asyncio.sleep(3600)  # Sleep, wake periodically
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        # Cleanup
        service.log.debug("Running teardown...")
        if asyncio.iscoroutinefunction(service.teardown_async):
            if service.teardown_async.__func__ is not Service.teardown_async:
                await service.teardown_async()
            else:
                service.teardown()
        else:
            service.teardown()
        service.log.debug("Teardown complete")


def run(service_class: Type[Service]):
    """
    Run a service. This is the main entry point.
    
    Usage:
        from jb_service import Service, method, run
        
        class MyService(Service):
            @method
            def hello(self, name: str) -> str:
                return f"Hello, {name}!"
        
        if __name__ == "__main__":
            run(MyService)
    """
    try:
        asyncio.run(run_async(service_class))
    except KeyboardInterrupt:
        pass
