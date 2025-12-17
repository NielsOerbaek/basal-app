from datetime import date, datetime
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.audit.middleware import get_current_user
from apps.audit.models import ActionType, ActivityLog
from apps.audit.registry import get_audit_config, is_audited

# Store pre-save state for comparison
_pre_save_state = {}


@receiver(pre_save)
def capture_pre_save_state(sender, instance, **kwargs):
    """Capture the state before save for comparison."""
    if not is_audited(sender):
        return

    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            _pre_save_state[(sender, instance.pk)] = {
                field.name: getattr(old_instance, field.name)
                for field in sender._meta.fields
            }
        except sender.DoesNotExist:
            pass


@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    """Log create and update actions."""
    if not is_audited(sender):
        return

    config = get_audit_config(sender)
    user = get_current_user()

    if created:
        action = ActionType.CREATE
        changes = {}
    else:
        action = ActionType.UPDATE
        changes = _calculate_changes(sender, instance, config)

        # Don't log if nothing changed
        if not changes:
            return

    # Get related entities
    related_school = None
    related_course = None

    if config.get_school:
        try:
            related_school = config.get_school(instance)
        except Exception:
            pass

    if config.get_course:
        try:
            related_course = config.get_course(instance)
        except Exception:
            pass

    ActivityLog.objects.create(
        user=user if user and user.is_authenticated else None,
        content_type=ContentType.objects.get_for_model(sender),
        object_id=instance.pk,
        object_repr=str(instance)[:255],
        action=action,
        changes=changes,
        related_school=related_school,
        related_course=related_course,
    )

    # Clean up pre-save state
    _pre_save_state.pop((sender, instance.pk), None)


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    """Log delete actions."""
    if not is_audited(sender):
        return

    config = get_audit_config(sender)
    user = get_current_user()

    # Get related entities before they're gone
    related_school = None
    related_course = None

    if config.get_school:
        try:
            related_school = config.get_school(instance)
        except Exception:
            pass

    if config.get_course:
        try:
            related_course = config.get_course(instance)
        except Exception:
            pass

    ActivityLog.objects.create(
        user=user if user and user.is_authenticated else None,
        content_type=ContentType.objects.get_for_model(sender),
        object_id=instance.pk,
        object_repr=str(instance)[:255],
        action=ActionType.DELETE,
        changes={},
        related_school=related_school,
        related_course=related_course,
    )


def _calculate_changes(sender, instance, config):
    """Calculate what fields changed."""
    old_state = _pre_save_state.get((sender, instance.pk), {})
    if not old_state:
        return {}

    changes = {}
    excluded = set(config.excluded_fields)
    tracked = set(config.tracked_fields) if config.tracked_fields else None

    for field in sender._meta.fields:
        name = field.name

        # Skip excluded fields
        if name in excluded:
            continue

        # Skip if not in tracked fields (when specified)
        if tracked and name not in tracked:
            continue

        old_value = old_state.get(name)
        new_value = getattr(instance, name)

        # Serialize for JSON comparison
        old_serialized = _serialize_value(old_value)
        new_serialized = _serialize_value(new_value)

        if old_serialized != new_serialized:
            changes[name] = {
                'old': old_serialized,
                'new': new_serialized,
            }

    return changes


def _serialize_value(value):
    """Serialize a value for JSON storage."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    # For FK fields, store the ID
    if hasattr(value, 'pk'):
        return value.pk
    return str(value)
