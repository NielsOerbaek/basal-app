from django.contrib.contenttypes.models import ContentType
from django.utils.decorators import method_decorator
from django.views.generic import ListView

from apps.audit.models import ActivityLog
from apps.core.decorators import staff_required
from apps.core.mixins import SortableMixin


@method_decorator(staff_required, name='dispatch')
class ActivityLogListView(SortableMixin, ListView):
    """View all activity across the system."""
    model = ActivityLog
    template_name = 'audit/activity_list.html'
    context_object_name = 'activities'
    paginate_by = 50

    sortable_fields = {
        'timestamp': 'timestamp',
        'action': 'action',
        'user': 'user__username',
        'type': 'content_type__model',
    }
    default_sort = 'timestamp'
    default_order = 'desc'

    def get_base_queryset(self):
        qs = super().get_base_queryset()
        qs = qs.select_related('user', 'content_type', 'related_school', 'related_course')

        # Filter by action type
        action = self.request.GET.get('action')
        if action:
            qs = qs.filter(action=action)

        # Filter by model type
        model_type = self.request.GET.get('type')
        if model_type:
            ct = ContentType.objects.filter(model=model_type).first()
            if ct:
                qs = qs.filter(content_type=ct)

        # Filter by user
        user_id = self.request.GET.get('user')
        if user_id:
            qs = qs.filter(user_id=user_id)

        return qs


@method_decorator(staff_required, name='dispatch')
class SchoolActivityListView(ListView):
    """View activity for a specific school."""
    model = ActivityLog
    template_name = 'audit/school_activity_list.html'
    context_object_name = 'activities'
    paginate_by = 50

    def get_queryset(self):
        school_id = self.kwargs['school_id']
        return ActivityLog.objects.filter(
            related_school_id=school_id
        ).select_related('user', 'content_type').order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.schools.models import School
        context['school'] = School.objects.get(pk=self.kwargs['school_id'])
        return context


@method_decorator(staff_required, name='dispatch')
class CourseActivityListView(ListView):
    """View activity for a specific course."""
    model = ActivityLog
    template_name = 'audit/course_activity_list.html'
    context_object_name = 'activities'
    paginate_by = 50

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return ActivityLog.objects.filter(
            related_course_id=course_id
        ).select_related('user', 'content_type').order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.courses.models import Course
        context['course'] = Course.objects.get(pk=self.kwargs['course_id'])
        return context
