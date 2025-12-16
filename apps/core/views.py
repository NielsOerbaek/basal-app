from django.db.models import Count
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from apps.contacts.models import ContactTime
from apps.courses.models import AttendanceStatus, Course, CourseSignUp
from apps.schools.models import School

from .decorators import staff_required


@method_decorator(staff_required, name='dispatch')
class DashboardView(TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        context['total_schools'] = School.objects.active().count()
        context['pending_signups'] = CourseSignUp.objects.filter(
            course__start_date__gte=now.date()
        ).count()
        context['courses_this_month'] = Course.objects.filter(
            start_date__year=now.year,
            start_date__month=now.month
        ).count()
        context['total_trained'] = CourseSignUp.objects.filter(
            attendance=AttendanceStatus.PRESENT
        ).count()

        context['upcoming_courses'] = Course.objects.filter(
            start_date__gte=now.date()
        ).annotate(
            signup_count_value=Count('signups')
        ).order_by('start_date')[:5]

        context['recent_contacts'] = ContactTime.objects.select_related(
            'school', 'created_by'
        )[:10]

        context['recent_signups'] = CourseSignUp.objects.select_related(
            'school', 'course'
        )[:10]

        return context
