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
    from jumpboot import MessagePackQueueServer, exposed
    
    # Create a dynamic server class that wraps our service
    class ServiceServer(MessagePackQueueServer):
        def __init__(self, service_instance):
            super().__init__()
            self.service = service_instance
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
    
    # Instantiate service first
    service = service_class()
    
    # Call setup
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    if asyncio.iscoroutinefunction(service_class.setup_async):
        if service_class.setup_async is not Service.setup_async:
            loop.run_until_complete(service.setup_async())
        else:
            service.setup()
    else:
        service.setup()
    
    # Create server
    server = ServiceServer(service)
    
    # Dynamically add exposed methods for each @method in service
    for method_name, method in service._methods.items():
        _add_exposed_method(server, service, method_name, method, loop)
    
    # Add introspection methods
    @exposed
    async def __jb_methods__() -> list:
        return service._list_methods()
    server.__jb_methods__ = __jb_methods__
    
    @exposed
    async def __jb_shutdown__() -> dict:
        if asyncio.iscoroutinefunction(type(service).teardown_async):
            if type(service).teardown_async is not Service.teardown_async:
                loop.run_until_complete(service.teardown_async())
            else:
                service.teardown()
        else:
            service.teardown()
        server.running = False
        return {"ok": True}
    server.__jb_shutdown__ = __jb_shutdown__
    
    # Run until stopped
    while server.running:
        time.sleep(0.1)


def _add_exposed_method(server, service: Service, method_name: str, method, loop):
    """Add an exposed method to the server for a service method."""
    from jumpboot import exposed
    
    fn = getattr(method, '_jb_original', method)
    hints = get_type_hints_safe(fn)
    
    # Create async wrapper
    async def handler(**kwargs):
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
                result = await method(**converted)
            else:
                result = method(**converted)
            
            return result
        
        except Exception as e:
            raise Exception(f"{type(e).__name__}: {str(e)}")
    
    # Apply exposed decorator and add to server
    handler.__name__ = method_name
    exposed_handler = exposed(handler)
    setattr(server, method_name, exposed_handler)
