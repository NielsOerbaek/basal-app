from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.decorators import staff_required
from apps.core.export import export_queryset_to_excel

from .forms import ContactTimeForm
from .models import ContactTime


@method_decorator(staff_required, name='dispatch')
class ContactListView(ListView):
    model = ContactTime
    template_name = 'contacts/contact_list.html'
    context_object_name = 'contacts'
    paginate_by = 25

    def get_queryset(self):
        queryset = ContactTime.objects.select_related('school', 'created_by')
        school_id = self.request.GET.get('school')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(school__name__icontains=search) |
                Q(comment__icontains=search)
            )
        return queryset


@method_decorator(staff_required, name='dispatch')
class ContactCreateView(CreateView):
    model = ContactTime
    form_class = ContactTimeForm
    template_name = 'contacts/contact_form.html'
    success_url = reverse_lazy('contacts:list')

    def get_initial(self):
        initial = super().get_initial()
        school_id = self.request.GET.get('school')
        if school_id:
            initial['school'] = school_id
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Henvendelse blev oprettet.')
        return response


@method_decorator(staff_required, name='dispatch')
class ContactDetailView(DetailView):
    model = ContactTime
    template_name = 'contacts/contact_detail.html'
    context_object_name = 'contact'

    def get_queryset(self):
        return ContactTime.objects.select_related('school', 'created_by')


@method_decorator(staff_required, name='dispatch')
class ContactUpdateView(UpdateView):
    model = ContactTime
    form_class = ContactTimeForm
    template_name = 'contacts/contact_form.html'

    def get_success_url(self):
        return reverse_lazy('contacts:detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Henvendelse blev opdateret.')
        return response


@method_decorator(staff_required, name='dispatch')
class ContactDeleteView(View):
    def get(self, request, pk):
        contact = get_object_or_404(ContactTime, pk=pk)
        return render(request, 'core/components/confirm_delete_modal.html', {
            'title': 'Slet henvendelse',
            'message': 'Er du sikker på, at du vil slette denne henvendelse?',
            'warning': 'Denne handling kan ikke fortrydes.',
            'delete_url': reverse_lazy('contacts:delete', kwargs={'pk': pk}),
        })

    def post(self, request, pk):
        contact = get_object_or_404(ContactTime, pk=pk)
        contact.delete()
        messages.success(request, 'Henvendelse er blevet slettet.')
        return JsonResponse({'success': True, 'redirect': str(reverse_lazy('contacts:list'))})


@method_decorator(staff_required, name='dispatch')
class ContactExportView(View):
    def get(self, request):
        queryset = ContactTime.objects.select_related('school', 'created_by')
        school_id = request.GET.get('school')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        fields = [
            ('school', 'Skole'),
            ('created_by', 'Oprettet af'),
            ('contacted_date', 'Dato'),
            ('contacted_time', 'Tidspunkt'),
            ('inbound', 'Kontaktede de os?'),
            ('comment', 'Kommentar'),
            ('created_at', 'Oprettet'),
        ]
        return export_queryset_to_excel(queryset, fields, 'contacts')
