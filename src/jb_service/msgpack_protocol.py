"""
MessagePack queue protocol for jb-service.

Uses jumpboot's MessagePackQueueServer for clean RPC without stdout interference.
"""
import asyncio
import traceback
from typing import Type, get_type_hints, Any
import inspect

from .service import Service
from .method import is_method, is_async_method
from .types import get_file_type_name, convert_file_param


def get_type_hints_safe(fn):
    """Get type hints, handling forward references gracefully."""
    try:
        return get_type_hints(fn)
    except Exception:
        return getattr(fn, '__annotations__', {})


def run_msgpack(service_class: Type[Service]):
    """
    Run a service using MessagePack queue transport.
    
    This uses jumpboot's MessagePackQueueServer for RPC communication,
    which keeps stdout/stderr separate from the protocol.
    """
    from jumpboot.queueserver import MessagePackQueueServer
    
    # Create server
    server = MessagePackQueueServer()
    
    # Instantiate service
    service = service_class()
    
    # Create async event loop for potential async methods
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Call setup
    if asyncio.iscoroutinefunction(service_class.setup_async):
        if service_class.setup_async is not Service.setup_async:
            loop.run_until_complete(service.setup_async())
        else:
            service.setup()
    else:
        service.setup()
    
    # Register each @method as a queue handler
    for method_name, method in service._methods.items():
        _register_method(server, service, method_name, method, loop)
    
    # Register introspection methods
    @server.register
    def __jb_methods__() -> list:
        """List available method names."""
        return service._list_methods()
    
    @server.register
    def __jb_shutdown__() -> dict:
        """Shutdown the service."""
        if asyncio.iscoroutinefunction(type(service).teardown_async):
            if type(service).teardown_async is not Service.teardown_async:
                loop.run_until_complete(service.teardown_async())
            else:
                service.teardown()
        else:
            service.teardown()
        return {"ok": True}
    
    # Run the server (blocks)
    server.run()


def _register_method(server, service: Service, method_name: str, method, loop):
    """Register a service method as a queue handler."""
    
    fn = getattr(method, '_jb_original', method)
    hints = get_type_hints_safe(fn)
    sig = inspect.signature(fn)
    
    def handler(**kwargs):
        """Handler for the queue server."""
        try:
            # Convert file parameters based on type hints
            converted = dict(kwargs)
            for param_name, annotation in hints.items():
                if param_name == 'return':
                    continue
                if param_name not in converted:
                    continue
                
                type_name = get_file_type_name(annotation)
                if type_name and isinstance(converted[param_name], str):
                    converted[param_name] = convert_file_param(
                        converted[param_name], type_name
                    )
            
            # Call the method
            if is_async_method(method):
                result = loop.run_until_complete(method(**converted))
            else:
                result = method(**converted)
            
            return result
        
        except Exception as e:
            # Return error in a structured format
            raise Exception(f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")
    
    # Register with the server
    server.register(handler, name=method_name)
