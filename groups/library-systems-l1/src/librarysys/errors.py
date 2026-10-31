"""Error types for the librarysys package (clean-room)."""
class LibrarySysError(Exception):
    """Base class for all librarysys errors."""
class ValidationError(LibrarySysError):
    """Input failed validation. Nothing was changed."""
class NotFoundError(LibrarySysError):
    """A requested object does not exist."""
class PermissionDenied(LibrarySysError):
    """The actor is not permitted to perform the requested action."""
