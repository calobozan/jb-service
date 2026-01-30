"""
MessagePack queue protocol for jb-service.

Uses jumpboot's MessagePackQueueServer for clean RPC without stdout interference.
"""
import asyncio
import time
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
    
    Note: The jumpboot module is injected at runtime by jumpboot.QueueProcess,
    not installed via pip.
    """
    # jumpboot is injected at runtime by QueueProcess
    from jumpboot import MessagePackQueueServer
    
    # Instantiate service first
    service = service_class()
    
    # Create event loop for async support
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
    
    # Create server without auto-exposing (we'll register manually)
    server = MessagePackQueueServer(auto_start=False, expose_methods=False)
    
    # Register each @method as a handler
    for method_name, method in service._methods.items():
        wrapper = _create_method_wrapper(service, method_name, method, loop)
        server.register_method(method_name, wrapper)
    
    # Register introspection methods
    async def jb_methods(data, request_id):
        return service._list_methods()
    server.register_method("__jb_methods__", jb_methods)
    
    async def jb_shutdown(data, request_id):
        if asyncio.iscoroutinefunction(type(service).teardown_async):
            if type(service).teardown_async is not Service.teardown_async:
                loop.run_until_complete(service.teardown_async())
            else:
                service.teardown()
        else:
            service.teardown()
        server.running = False
        return {"ok": True}
    server.register_method("__jb_shutdown__", jb_shutdown)
    
    # Start and run
    server.start()
    while server.running:
        time.sleep(0.1)


def _create_method_wrapper(service: Service, method_name: str, method, loop):
    """Create an async wrapper for a service method."""
    fn = getattr(method, '_jb_original', method)
    hints = get_type_hints_safe(fn)
    
    async def wrapper(data, request_id):
        try:
            # Convert data to kwargs
            kwargs = data if isinstance(data, dict) else {}
            
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
                result = await method(**converted)
            else:
                result = method(**converted)
            
            return result
        
        except Exception as e:
            # Re-raise with traceback info
            raise Exception(f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")
    
    return wrapper
