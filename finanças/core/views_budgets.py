"""Budget CRUD views."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import BudgetForm
from .models import Budget
from .services import budget_spent_map


class BudgetListView(LoginRequiredMixin, ListView):
    model = Budget
    template_name = "core/budget_list.html"
    context_object_name = "budgets"

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user).select_related("category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budgets = context["budgets"]
        spent_map = budget_spent_map(self.request.user, budgets)

        for budget in budgets:
            spent = spent_map.get(budget.id) or 0
            budget.spent = spent
            budget.percentage = (spent / budget.limit) * 100 if budget.limit > 0 else 0

            if budget.percentage >= 100:
                budget.status_color = "danger"
            elif budget.percentage >= 75:
                budget.status_color = "warning"
            else:
                budget.status_color = "success"

        return context


class BudgetCreateView(LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = "core/form.html"
    success_url = reverse_lazy("budget_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = "core/form.html"
    success_url = reverse_lazy("budget_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)


class BudgetDeleteView(LoginRequiredMixin, DeleteView):
    model = Budget
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("budget_list")

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)
