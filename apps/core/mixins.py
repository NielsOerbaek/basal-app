class SortableMixin:
    """
    Mixin for ListView that adds sorting support.

    Define `sortable_fields` as a dict mapping URL param names to model fields.
    Define `default_sort` as the default sort field (optional).
    Override `get_base_queryset` to provide filtered queryset before sorting.
    """
    sortable_fields = {}
    default_sort = None
    default_order = 'asc'

    def get_sort_params(self):
        sort = self.request.GET.get('sort', self.default_sort)
        order = self.request.GET.get('order', self.default_order)
        if order not in ('asc', 'desc'):
            order = self.default_order
        return sort, order

    def get_base_queryset(self):
        """Override this to provide the base queryset before sorting."""
        return super().get_queryset()

    def get_queryset(self):
        queryset = self.get_base_queryset()
        sort, order = self.get_sort_params()

        if sort and sort in self.sortable_fields:
            field = self.sortable_fields[sort]
            if order == 'desc':
                field = f'-{field}'
            queryset = queryset.order_by(field)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sort, order = self.get_sort_params()
        context['current_sort'] = sort
        context['current_order'] = order
        context['sortable_fields'] = self.sortable_fields
        return context
