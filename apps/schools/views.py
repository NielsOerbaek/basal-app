from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.export import export_queryset_to_excel

from .forms import SchoolForm
from .models import School


@method_decorator(staff_member_required, name='dispatch')
class SchoolListView(ListView):
    model = School
    template_name = 'schools/school_list.html'
    context_object_name = 'schools'
    paginate_by = 25

    def get_queryset(self):
        queryset = School.objects.active()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(location__icontains=search) |
                Q(contact_name__icontains=search) |
                Q(contact_email__icontains=search)
            )
        return queryset


@method_decorator(staff_member_required, name='dispatch')
class SchoolCreateView(CreateView):
    model = School
    form_class = SchoolForm
    template_name = 'schools/school_form.html'
    success_url = reverse_lazy('schools:list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Skolen "{self.object.name}" blev oprettet.')
        return response


@method_decorator(staff_member_required, name='dispatch')
class SchoolDetailView(DetailView):
    model = School
    template_name = 'schools/school_detail.html'
    context_object_name = 'school'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contact_history'] = self.object.contact_history.select_related(
            'employee', 'employee__user'
        )[:10]
        context['course_signups'] = self.object.course_signups.select_related(
            'course'
        ).order_by('-course__datetime')[:10]
        return context


@method_decorator(staff_member_required, name='dispatch')
class SchoolUpdateView(UpdateView):
    model = School
    form_class = SchoolForm
    template_name = 'schools/school_form.html'

    def get_success_url(self):
        return reverse_lazy('schools:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Skolen "{self.object.name}" blev opdateret.')
        return response


@method_decorator(staff_member_required, name='dispatch')
class SchoolDeleteView(View):
    def get(self, request, pk):
        school = School.objects.get(pk=pk)
        return render(request, 'core/components/confirm_delete_modal.html', {
            'title': 'Deaktiver skole',
            'message': f'Er du sikker på, at du vil deaktivere <strong>{school.name}</strong>?',
            'warning': 'Skolen vil blive skjult, men dens data bevares.',
            'delete_url': reverse_lazy('schools:delete', kwargs={'pk': pk}),
            'button_text': 'Deaktiver',
        })

    def post(self, request, pk):
        school = School.objects.get(pk=pk)
        school_name = school.name
        school.delete()
        messages.success(request, f'Skolen "{school_name}" er blevet deaktiveret.')
        return JsonResponse({'success': True, 'redirect': str(reverse_lazy('schools:list'))})


@method_decorator(staff_member_required, name='dispatch')
class SchoolExportView(View):
    def get(self, request):
        queryset = School.objects.active()
        fields = [
            ('name', 'Navn'),
            ('location', 'Adresse'),
            ('contact_name', 'Kontaktperson'),
            ('contact_email', 'Kontakt e-mail'),
            ('contact_phone', 'Kontakt telefon'),
            ('created_at', 'Oprettet'),
        ]
        return export_queryset_to_excel(queryset, fields, 'schools')


class SchoolAutocompleteView(View):
    def get(self, request):
        query = request.GET.get('q', '')
        schools = School.objects.active().filter(name__icontains=query)[:10]
        results = [{'id': s.pk, 'name': s.name, 'location': s.location} for s in schools]
        return JsonResponse({'results': results})
