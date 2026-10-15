"""Errors that services raise when a rule is broken.

Services know nothing about HTTP: app/main.py is the one place that maps each error to a status code.
The message is shown to the user, so it should say what went wrong.
"""


class ServiceError(Exception):
    """Base class for every rule a request can break."""


class NotAuthenticated(ServiceError):
    """No valid sign-in: wrong email or password, or a missing, invalid or expired token."""


class PermissionDenied(ServiceError):
    """Signed in, but the caller's role may not do this."""


class NotFound(ServiceError):
    """The thing doesn't exist, or the caller isn't allowed to know that it exists."""


class Conflict(ServiceError):
    """The request clashes with the current state, e.g. a lesson order that doesn't match the course's lessons."""


class InvalidInput(ServiceError):
    """The request can't be used as sent, e.g. a pasted list with no addresses in it, or too many."""
