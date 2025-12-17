from django.contrib import messages
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.export import export_queryset_to_excel
from apps.core.decorators import staff_required
from apps.core.mixins import SortableMixin

from .forms import SchoolForm, SeatPurchaseForm, PersonForm, SchoolCommentForm
from .models import School, SeatPurchase, Person, SchoolComment


@method_decorator(staff_required, name='dispatch')
class KommuneListView(SortableMixin, ListView):
    template_name = 'schools/kommune_list.html'
    context_object_name = 'kommuner'
    sortable_fields = {
        'kommune': 'kommune',
        'total': 'total_schools',
        'enrolled': 'enrolled_schools',
        'not_enrolled': 'not_enrolled',
    }
    default_sort = 'kommune'

    def get_base_queryset(self):
        return (
            School.objects.active()
            .values('kommune')
            .annotate(
                total_schools=Count('id'),
                enrolled_schools=Count('id', filter=Q(enrolled_at__isnull=False)),
                not_enrolled=F('total_schools') - F('enrolled_schools')
            )
        )


@method_decorator(staff_required, name='dispatch')
class KommuneDetailView(ListView):
    template_name = 'schools/kommune_detail.html'
    context_object_name = 'schools'

    def get_queryset(self):
        return (
            School.objects.active()
            .filter(kommune=self.kwargs['kommune'])
            .prefetch_related('people')
            .order_by('name')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['kommune'] = self.kwargs['kommune']
        return context


@method_decorator(staff_required, name='dispatch')
class SchoolListView(SortableMixin, ListView):
    model = School
    template_name = 'schools/school_list.html'
    context_object_name = 'schools'
    paginate_by = 25
    sortable_fields = {
        'name': 'name',
        'kommune': 'kommune',
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
                Q(adresse__icontains=search) |
                Q(kommune__icontains=search) |
                Q(people__name__icontains=search) |
                Q(people__email__icontains=search)
            ).distinct()
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
        context['people'] = self.object.people.all()
        context['school_comments'] = self.object.school_comments.select_related('created_by').all()
        context['person_form'] = PersonForm()
        context['comment_form'] = SchoolCommentForm()
        context['recent_activities'] = self.object.activity_logs.select_related(
            'user', 'content_type'
        )[:5]
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
            ('adresse', 'Adresse'),
            ('kommune', 'Kommune'),
            ('enrolled_at', 'Tilmeldt'),
            ('created_at', 'Oprettet'),
        ]
        return export_queryset_to_excel(queryset, fields, 'schools')


class SchoolAutocompleteView(View):
    def get(self, request):
        query = request.GET.get('q', '')
        schools = School.objects.active().filter(name__icontains=query)[:10]
        results = [{'id': s.pk, 'name': s.name, 'kommune': s.kommune} for s in schools]
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


@method_decorator(staff_required, name='dispatch')
class PersonCreateView(View):
    def get(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = PersonForm()
        return render(request, 'schools/person_form.html', {
            'school': school,
            'form': form,
        })

    def post(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = PersonForm(request.POST)
        if form.is_valid():
            person = form.save(commit=False)
            person.school = school
            person.save()
            messages.success(request, f'Person "{person.name}" tilføjet.')
            return redirect('schools:detail', pk=school.pk)
        return render(request, 'schools/person_form.html', {
            'school': school,
            'form': form,
        })


@method_decorator(staff_required, name='dispatch')
class PersonUpdateView(View):
    def get(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        form = PersonForm(instance=person)
        return render(request, 'schools/person_form.html', {
            'school': person.school,
            'form': form,
            'person': person,
        })

    def post(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        form = PersonForm(request.POST, instance=person)
        if form.is_valid():
            form.save()
            messages.success(request, f'Person "{person.name}" opdateret.')
            return redirect('schools:detail', pk=person.school.pk)
        return render(request, 'schools/person_form.html', {
            'school': person.school,
            'form': form,
            'person': person,
        })


@method_decorator(staff_required, name='dispatch')
class PersonDeleteView(View):
    def get(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        return render(request, 'core/components/confirm_delete_modal.html', {
            'title': 'Slet person',
            'message': f'Er du sikker på, at du vil slette <strong>{person.name}</strong>?',
            'delete_url': reverse_lazy('schools:person-delete', kwargs={'pk': pk}),
            'button_text': 'Slet',
        })

    def post(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        school_pk = person.school.pk
        person_name = person.name
        person.delete()
        messages.success(request, f'Person "{person_name}" er blevet slettet.')
        return JsonResponse({'success': True, 'redirect': str(reverse_lazy('schools:detail', kwargs={'pk': school_pk}))})


@method_decorator(staff_required, name='dispatch')
class SchoolCommentCreateView(View):
    def get(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = SchoolCommentForm()
        return render(request, 'schools/comment_form.html', {
            'school': school,
            'form': form,
        })

    def post(self, request, school_pk):
        school = get_object_or_404(School, pk=school_pk)
        form = SchoolCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.school = school
            comment.created_by = request.user
            comment.save()
            messages.success(request, 'Kommentar tilføjet.')
            return redirect('schools:detail', pk=school.pk)
        return render(request, 'schools/comment_form.html', {
            'school': school,
            'form': form,
        })


@method_decorator(staff_required, name='dispatch')
class SchoolCommentDeleteView(View):
    def get(self, request, pk):
        comment = get_object_or_404(SchoolComment, pk=pk)
        return render(request, 'core/components/confirm_delete_modal.html', {
            'title': 'Slet kommentar',
            'message': 'Er du sikker på, at du vil slette denne kommentar?',
            'delete_url': reverse_lazy('schools:comment-delete', kwargs={'pk': pk}),
            'button_text': 'Slet',
        })

    def post(self, request, pk):
        comment = get_object_or_404(SchoolComment, pk=pk)
        school_pk = comment.school.pk
        comment.delete()
        messages.success(request, 'Kommentar er blevet slettet.')
        return JsonResponse({'success': True, 'redirect': str(reverse_lazy('schools:detail', kwargs={'pk': school_pk}))})
