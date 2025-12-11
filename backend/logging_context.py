"""
Logging context variables for request tracking.

This module provides context variables that can be used across the application
to track request IDs and user IDs for structured logging.
"""
from contextvars import ContextVar
from typing import Optional

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)

