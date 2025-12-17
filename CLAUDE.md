# Basal App Development Notes

## Activity Log (Audit)

When adding new models that should be tracked in the activity log, register them in `apps/audit/apps.py`:

```python
from apps.newapp.models import NewModel

register_for_audit(NewModel, AuditCfg(
    excluded_fields=['id', 'created_at', 'updated_at'],
    get_school=lambda instance: instance.school,  # if applicable
    get_course=lambda instance: instance.course,  # if applicable
))
```

The `AuditConfig` options:
- `tracked_fields` - List of fields to track (None = all fields)
- `excluded_fields` - Fields to exclude from tracking (default: id, created_at, updated_at)
- `get_school` - Lambda to get related school for filtering
- `get_course` - Lambda to get related course for filtering
