from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.export import export_queryset_to_excel
from apps.core.decorators import staff_required
from apps.core.mixins import SortableMixin

from .forms import SchoolForm, SeatPurchaseForm
from .models import School, SeatPurchase


@method_decorator(staff_required, name='dispatch')
class SchoolListView(SortableMixin, ListView):
    model = School
    template_name = 'schools/school_list.html'
    context_object_name = 'schools'
    paginate_by = 25
    sortable_fields = {
        'name': 'name',
        'location': 'location',
        'contact': 'contact_name',
        'seats': '_remaining_seats',  # Special handling for computed property
    }
    default_sort = 'name'

    def get_base_queryset(self):
        """Return the base queryset before sorting."""
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

    def get_queryset(self):
        """Handle special sorting for computed fields."""
        sort, order = self.get_sort_params()

        # For seats sorting, we need to sort in Python since it's a computed property
        if sort == 'seats':
            queryset = list(self.get_base_queryset())
            reverse = (order == 'desc')
            queryset.sort(key=lambda s: s.remaining_seats, reverse=reverse)
            return queryset

        # Use default mixin sorting for other fields
        return super().get_queryset()


@method_decorator(staff_required, name='dispatch')
class SchoolCreateView(CreateView):
    model = School
    form_class = SchoolForm
    template_name = 'schools/school_form.html'
    success_url = reverse_lazy('schools:list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Skolen "{self.object.name}" blev oprettet.')
        return response


@method_decorator(staff_required, name='dispatch')
class SchoolDetailView(DetailView):
    model = School
    template_name = 'schools/school_detail.html'
    context_object_name = 'school'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contact_history'] = self.object.contact_history.select_related(
            'created_by'
        )[:10]
        context['course_signups'] = self.object.course_signups.select_related(
            'course'
        ).order_by('-course__start_date')[:10]
        context['seat_purchases'] = self.object.seat_purchases.all()
        return context


@method_decorator(staff_required, name='dispatch')
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


@method_decorator(staff_required, name='dispatch')
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


@method_decorator(staff_required, name='dispatch')
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


@method_decorator(staff_required, name='dispatch')
class AddSeatsView(View):
    def get(self, request, pk):
        school = get_object_or_404(School, pk=pk)
        form = SeatPurchaseForm()
        return render(request, 'schools/add_seats.html', {
            'school': school,
            'form': form,
        })

    def post(self, request, pk):
        school = get_object_or_404(School, pk=pk)
        form = SeatPurchaseForm(request.POST)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.school = school
            purchase.save()
            messages.success(request, f'{purchase.seats} pladser tilføjet til "{school.name}".')
            return redirect('schools:detail', pk=school.pk)
        return render(request, 'schools/add_seats.html', {
            'school': school,
            'form': form,
        })
