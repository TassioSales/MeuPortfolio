"""Category CRUD views."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import CategoryForm
from .models import Category


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = "core/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        qs = Category.objects.filter(user=self.request.user).select_related("parent")

        search = self.request.GET.get("search", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)

        type_ = self.request.GET.get("type", "")
        if type_ in ("RECEITA", "DESPESA"):
            qs = qs.filter(type=type_)

        parent = self.request.GET.get("parent", "")
        if parent == "none":
            qs = qs.filter(parent__isnull=True)
        elif parent:
            # Show the selected parent category together with its subcategories.
            qs = qs.filter(Q(pk=parent) | Q(parent_id=parent))

        return qs.order_by("parent__name", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent_categories"] = Category.objects.filter(
            user=self.request.user, parent__isnull=True
        ).order_by("name")
        context["filter_search"] = self.request.GET.get("search", "")
        context["filter_type"] = self.request.GET.get("type", "")
        context["filter_parent"] = self.request.GET.get("parent", "")
        return context


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "core/form.html"
    success_url = reverse_lazy("category_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "core/form.html"
    success_url = reverse_lazy("category_list")

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("category_list")

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)
