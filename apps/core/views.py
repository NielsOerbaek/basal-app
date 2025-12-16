from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from apps.contacts.models import ContactTime
from apps.courses.models import AttendanceStatus, Course, CourseSignUp
from apps.schools.models import School


@method_decorator(staff_member_required, name='dispatch')
class DashboardView(TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        context['total_schools'] = School.objects.active().count()
        context['pending_signups'] = CourseSignUp.objects.filter(
            course__datetime__gte=now
        ).count()
        context['courses_this_month'] = Course.objects.filter(
            datetime__year=now.year,
            datetime__month=now.month
        ).count()
        context['total_trained'] = CourseSignUp.objects.filter(
            attendance=AttendanceStatus.PRESENT
        ).count()

        context['upcoming_courses'] = Course.objects.filter(
            datetime__gte=now
        ).annotate(
            signup_count_value=Count('signups')
        ).order_by('datetime')[:5]

        context['recent_contacts'] = ContactTime.objects.select_related(
            'school', 'created_by'
        )[:10]

        context['recent_signups'] = CourseSignUp.objects.select_related(
            'school', 'course'
        )[:10]

        return context
