from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.core.decorators import staff_required
from apps.core.export import export_queryset_to_excel

from .forms import CourseForm, CourseSignUpForm, PublicSignUpForm
from .models import AttendanceStatus, Course, CourseSignUp


@method_decorator(staff_required, name='dispatch')
class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 25

    def get_queryset(self):
        queryset = Course.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(location__icontains=search)
            )
        return queryset


@method_decorator(staff_required, name='dispatch')
class CourseCreateView(CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('courses:list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Kurset "{self.object.title}" blev oprettet.')
        return response


@method_decorator(staff_required, name='dispatch')
class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['signups'] = self.object.signups.select_related('school').all()
        return context


@method_decorator(staff_required, name='dispatch')
class CourseUpdateView(UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'

    def get_success_url(self):
        return reverse_lazy('courses:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Kurset "{self.object.title}" blev opdateret.')
        return response


@method_decorator(staff_required, name='dispatch')
class CourseDeleteView(View):
    def get(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        return render(request, 'core/components/confirm_delete_modal.html', {
            'title': 'Slet kursus',
            'message': f'Er du sikker på, at du vil slette <strong>{course.title}</strong>?',
            'warning': 'Dette vil også slette alle tilmeldinger til dette kursus. Denne handling kan ikke fortrydes.',
            'delete_url': reverse_lazy('courses:delete', kwargs={'pk': pk}),
        })

    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        course_title = course.title
        course.delete()
        messages.success(request, f'Kurset "{course_title}" er blevet slettet.')
        return JsonResponse({'success': True, 'redirect': str(reverse_lazy('courses:list'))})


@method_decorator(staff_required, name='dispatch')
class CourseExportView(View):
    def get(self, request):
        queryset = Course.objects.all()
        fields = [
            ('title', 'Titel'),
            ('start_date', 'Startdato'),
            ('end_date', 'Slutdato'),
            ('location', 'Lokation'),
            ('capacity', 'Kapacitet'),
            ('signup_count', 'Tilmeldinger'),
            ('is_published', 'Offentliggjort'),
        ]
        return export_queryset_to_excel(queryset, fields, 'courses')


@method_decorator(staff_required, name='dispatch')
class SignUpListView(ListView):
    model = CourseSignUp
    template_name = 'courses/signup_list.html'
    context_object_name = 'signups'
    paginate_by = 25

    def get_queryset(self):
        queryset = CourseSignUp.objects.select_related('school', 'course')
        course_id = self.request.GET.get('course')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(participant_name__icontains=search) |
                Q(school__name__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['courses'] = Course.objects.all()
        return context


@method_decorator(staff_required, name='dispatch')
class SignUpExportView(View):
    def get(self, request):
        queryset = CourseSignUp.objects.select_related('school', 'course')
        course_id = request.GET.get('course')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        fields = [
            ('course', 'Kursus'),
            ('school', 'Skole'),
            ('participant_name', 'Deltager'),
            ('participant_title', 'Titel'),
            ('attendance', 'Fremmøde'),
            ('created_at', 'Tilmeldt'),
        ]
        return export_queryset_to_excel(queryset, fields, 'signups')


@method_decorator(staff_required, name='dispatch')
class RollCallView(DetailView):
    model = Course
    template_name = 'courses/rollcall.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        signups = self.object.signups.select_related('school').order_by('school__name', 'participant_name')
        context['signups'] = signups
        context['total'] = signups.count()
        context['present'] = signups.filter(attendance=AttendanceStatus.PRESENT).count()
        context['absent'] = signups.filter(attendance=AttendanceStatus.ABSENT).count()
        context['unmarked'] = signups.filter(attendance=AttendanceStatus.UNMARKED).count()
        return context


@method_decorator(staff_required, name='dispatch')
class MarkAttendanceView(View):
    def post(self, request, pk):
        signup = get_object_or_404(CourseSignUp, pk=pk)
        attendance = request.POST.get('attendance')
        if attendance in [choice[0] for choice in AttendanceStatus.choices]:
            signup.attendance = attendance
            signup.save()
        return render(request, 'courses/partials/rollcall_row.html', {'signup': signup})


class PublicSignUpView(View):
    template_name = 'courses/public_signup.html'

    def get(self, request):
        form = PublicSignUpForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PublicSignUpForm(request.POST)
        if form.is_valid():
            CourseSignUp.objects.create(
                course=form.cleaned_data['course'],
                school=form.cleaned_data['school'],
                participant_name=form.cleaned_data['participant_name'],
                participant_title=form.cleaned_data.get('participant_title', ''),
            )
            return redirect('signup-success')

        return render(request, self.template_name, {'form': form})


class SignUpSuccessView(TemplateView):
    template_name = 'courses/signup_success.html'
