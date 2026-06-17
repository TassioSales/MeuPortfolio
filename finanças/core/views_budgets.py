"""Budget CRUD views."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import BudgetForm
from .models import Budget, Transaction


class BudgetListView(LoginRequiredMixin, ListView):
    model = Budget
    template_name = "core/budget_list.html"
    context_object_name = "budgets"

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budgets = context["budgets"]
        today = timezone.now().date()

        for budget in budgets:
            if budget.period == "MENSAL":
                transactions = Transaction.objects.filter(
                    user=self.request.user,
                    category=budget.category,
                    type="DESPESA",
                    date__year=today.year,
                    date__month=today.month,
                )
            else:
                transactions = Transaction.objects.filter(
                    user=self.request.user,
                    category=budget.category,
                    type="DESPESA",
                    date__year=today.year,
                )

            spent = transactions.aggregate(Sum("amount"))["amount__sum"] or 0
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

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = "core/form.html"
    success_url = reverse_lazy("budget_list")

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)


class BudgetDeleteView(LoginRequiredMixin, DeleteView):
    model = Budget
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("budget_list")

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)
