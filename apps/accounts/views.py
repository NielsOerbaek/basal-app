from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import UserCreateForm, UserUpdateForm
from .models import Employee


def superuser_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'Du skal være superbruger for at få adgang til denne side.')
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@method_decorator([staff_member_required, superuser_required], name='dispatch')
class UserListView(ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_queryset(self):
        queryset = User.objects.select_related('employee_profile').order_by(
            'first_name', 'last_name', 'username'
        )
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        return queryset


@method_decorator([staff_member_required, superuser_required], name='dispatch')
class UserCreateView(CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        Employee.objects.create(user=self.object)
        messages.success(self.request, f'Brugeren "{self.object.username}" blev oprettet.')
        return response


@method_decorator([staff_member_required, superuser_required], name='dispatch')
class UserDetailView(DetailView):
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user_obj'


@method_decorator([staff_member_required, superuser_required], name='dispatch')
class UserUpdateView(UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/user_form.html'
    context_object_name = 'user_obj'

    def get_success_url(self):
        return reverse_lazy('accounts:user-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Brugeren "{self.object.username}" blev opdateret.')
        return response


@method_decorator([staff_member_required, superuser_required], name='dispatch')
class UserToggleActiveView(View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, 'Du kan ikke deaktivere dig selv.')
        else:
            user.is_active = not user.is_active
            user.save()
            status = 'aktiveret' if user.is_active else 'deaktiveret'
            messages.success(request, f'Brugeren "{user.username}" er blevet {status}.')
        return redirect('accounts:user-list')
