from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.core.decorators import staff_required
from apps.core.export import export_queryset_to_excel
from apps.core.mixins import SortableMixin

from .forms import CourseForm, CourseSignUpForm, PublicSignUpForm
from .models import AttendanceStatus, Course, CourseSignUp


@method_decorator(staff_required, name='dispatch')
class CourseListView(SortableMixin, ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 25
    sortable_fields = {
        'title': 'title',
        'date': 'start_date',
        'location': 'location',
    }
    default_sort = 'date'
    default_order = 'desc'

    def get_base_queryset(self):
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
        context['recent_activities'] = self.object.activity_logs.select_related(
            'user', 'content_type'
        )[:5]
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
            'message': format_html('Er du sikker på, at du vil slette <strong>{}</strong>?', course.title),
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


@method_decorator(staff_required, name='dispatch')
class SignUpDeleteView(View):
    def get(self, request, pk):
        signup = get_object_or_404(CourseSignUp, pk=pk)
        return render(request, 'core/components/confirm_delete_modal.html', {
            'title': 'Slet tilmelding',
            'message': format_html('Er du sikker på, at du vil slette tilmeldingen for <strong>{}</strong>?', signup.participant_name),
            'delete_url': reverse('courses:signup-delete', kwargs={'pk': pk}),
        })

    def post(self, request, pk):
        signup = get_object_or_404(CourseSignUp, pk=pk)
        course_pk = signup.course.pk
        signup.delete()
        messages.success(request, 'Tilmeldingen er blevet slettet.')
        return JsonResponse({'success': True, 'redirect': reverse('courses:detail', kwargs={'pk': course_pk})})


class PublicSignUpView(View):
    template_name = 'courses/public_signup.html'

    def get(self, request):
        form = PublicSignUpForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PublicSignUpForm(request.POST)
        if form.is_valid():
            signup = CourseSignUp.objects.create(
                course=form.cleaned_data['course'],
                school=form.cleaned_data['school'],
                participant_name=form.cleaned_data['participant_name'],
                participant_email=form.cleaned_data['participant_email'],
                participant_title=form.cleaned_data.get('participant_title', ''),
            )
            # Send confirmation email
            from apps.emails.services import send_signup_confirmation
            send_signup_confirmation(signup)

            return redirect('signup-success')

        return render(request, self.template_name, {'form': form})


class SignUpSuccessView(TemplateView):
    template_name = 'courses/signup_success.html'


class CheckSchoolSeatsView(View):
    """AJAX endpoint to check if a school has available seats."""

    def get(self, request):
        from apps.schools.models import School
        school_id = request.GET.get('school_id')
        if not school_id:
            return JsonResponse({'error': 'Missing school_id'}, status=400)
        try:
            school = School.objects.get(pk=school_id)
            return JsonResponse({
                'has_available_seats': school.has_available_seats,
                'remaining_seats': school.remaining_seats,
            })
        except School.DoesNotExist:
            return JsonResponse({'error': 'School not found'}, status=404)


@method_decorator(staff_required, name='dispatch')
class BulkImportView(View):
    """Bulk import signups by pasting from Excel."""

    def get(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        return render(request, 'courses/bulk_import_modal.html', {'course': course})

    def post(self, request, pk):
        from apps.schools.models import School

        course = get_object_or_404(Course, pk=pk)
        raw_data = request.POST.get('data', '')

        # Parse pasted data (tab-separated: name, school, email)
        rows = []
        lines = raw_data.strip().split('\n')

        for i, line in enumerate(lines):
            if not line.strip():
                continue

            # Split by tab (Excel default) or multiple spaces
            parts = line.split('\t')
            if len(parts) < 2:
                parts = [p.strip() for p in line.split('  ') if p.strip()]

            if len(parts) < 2:
                continue

            # Skip header row
            if i == 0 and parts[0].lower() in ['navn', 'name', 'deltager']:
                continue

            name = parts[0].strip()
            school_name = parts[1].strip() if len(parts) > 1 else ''
            email = parts[2].strip() if len(parts) > 2 else ''

            if not name or not school_name:
                continue

            # Find matching schools
            matches = self._find_school_matches(school_name)

            rows.append({
                'index': len(rows),
                'name': name,
                'school_name': school_name,
                'email': email,
                'matches': matches,
                'exact_match': matches[0] if matches and matches[0].name.lower() == school_name.lower() else None,
            })

        if not rows:
            messages.error(request, 'Ingen gyldige rækker fundet. Forventet format: Navn, Skole, Email (tab-separeret)')
            return render(request, 'courses/bulk_import_modal.html', {'course': course})

        # Get all schools for fallback dropdown
        all_schools = School.objects.active().order_by('name')

        return render(request, 'courses/bulk_import_match.html', {
            'course': course,
            'rows': rows,
            'all_schools': all_schools,
        })

    def _find_school_matches(self, search_term):
        from apps.schools.models import School

        if not search_term:
            return []

        # Try exact match first
        exact = School.objects.active().filter(name__iexact=search_term).first()
        if exact:
            return [exact]

        # Find schools containing the search term
        contains = list(School.objects.active().filter(name__icontains=search_term)[:5])

        # Find schools where search term contains school name
        if len(contains) < 5:
            all_schools = School.objects.active()
            for school in all_schools:
                if school.name.lower() in search_term.lower() and school not in contains:
                    contains.append(school)
                    if len(contains) >= 5:
                        break

        # Sort by name length similarity
        contains.sort(key=lambda s: abs(len(s.name) - len(search_term)))

        return contains[:5]


@method_decorator(staff_required, name='dispatch')
class BulkImportConfirmView(View):
    """Process confirmed bulk import."""

    def post(self, request, pk):
        from apps.schools.models import School

        course = get_object_or_404(Course, pk=pk)

        # Get form data
        count = int(request.POST.get('count', 0))
        created = 0
        skipped = 0
        errors = []

        for i in range(count):
            school_id = request.POST.get(f'school_{i}')
            name = request.POST.get(f'name_{i}')
            email = request.POST.get(f'email_{i}', '')

            if not school_id or school_id == 'skip':
                skipped += 1
                continue

            try:
                school = School.objects.get(pk=school_id)

                # Check for duplicate
                if CourseSignUp.objects.filter(course=course, school=school, participant_name=name).exists():
                    errors.append(f'{name} ({school.name}) er allerede tilmeldt')
                    continue

                CourseSignUp.objects.create(
                    course=course,
                    school=school,
                    participant_name=name,
                    participant_email=email,
                )
                created += 1

            except School.DoesNotExist:
                errors.append(f'Skole ikke fundet for {name}')
            except Exception as e:
                errors.append(f'Fejl ved oprettelse af {name}: {str(e)}')

        # Build result message
        msg_parts = []
        if created:
            msg_parts.append(f'{created} tilmelding{"er" if created != 1 else ""} oprettet')
        if skipped:
            msg_parts.append(f'{skipped} sprunget over')
        if errors:
            msg_parts.append(f'{len(errors)} fejl')

        if created:
            messages.success(request, '. '.join(msg_parts) + '.')
        elif errors:
            messages.error(request, '. '.join(msg_parts) + '.')
        else:
            messages.warning(request, 'Ingen tilmeldinger oprettet.')

        if errors:
            for error in errors[:5]:  # Show max 5 errors
                messages.warning(request, error)

        return redirect('courses:detail', pk=course.pk)
