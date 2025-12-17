from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class AuditConfig:
    """Configuration for auditing a model."""
    # Fields to track (None = all fields)
    tracked_fields: Optional[List[str]] = None
    # Fields to exclude from tracking
    excluded_fields: List[str] = field(default_factory=lambda: ['id', 'created_at', 'updated_at'])
    # Function to get related school: (instance) -> School or None
    get_school: Optional[Callable] = None
    # Function to get related course: (instance) -> Course or None
    get_course: Optional[Callable] = None


# Global registry
_audit_registry: dict = {}


def register_for_audit(model_class, config: AuditConfig = None):
    """
    Register a model for automatic audit logging.

    Usage:
        register_for_audit(School, AuditConfig(
            excluded_fields=['created_at', 'updated_at'],
            get_school=lambda instance: instance,
        ))
    """
    if config is None:
        config = AuditConfig()
    _audit_registry[model_class] = config
    return model_class


def get_audit_config(model_class) -> Optional[AuditConfig]:
    """Get audit configuration for a model."""
    return _audit_registry.get(model_class)


def is_audited(model_class) -> bool:
    """Check if a model is registered for auditing."""
    return model_class in _audit_registry
