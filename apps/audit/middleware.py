import threading

_thread_locals = threading.local()


def get_current_user():
    """Get the current user from thread-local storage."""
    return getattr(_thread_locals, 'user', None)


def get_current_request():
    """Get the current request from thread-local storage."""
    return getattr(_thread_locals, 'request', None)


class AuditMiddleware:
    """
    Middleware to store the current request/user in thread-local storage.
    This allows signals to access the current user.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        _thread_locals.user = getattr(request, 'user', None)

        try:
            response = self.get_response(request)
        finally:
            # Clean up
            _thread_locals.request = None
            _thread_locals.user = None

        return response
