"""Goal CRUD + quick deposit views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import GoalDepositForm, GoalForm
from .models import Goal


class GoalListView(LoginRequiredMixin, ListView):
    model = Goal
    template_name = "core/goal_list.html"
    context_object_name = "goals"

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        goals = ctx["goals"]
        total_target = sum(g.target_amount for g in goals)
        total_saved = sum(g.current_amount for g in goals)
        ctx.update({
            "total_target": total_target,
            "total_saved": total_saved,
            "overall_pct": int((total_saved / total_target) * 100) if total_target else 0,
            "deposit_form": GoalDepositForm(),
        })
        return ctx


class GoalCreateView(LoginRequiredMixin, CreateView):
    model = Goal
    form_class = GoalForm
    template_name = "core/goal_form.html"
    success_url = reverse_lazy("goal_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Meta criada com sucesso!")
        return super().form_valid(form)


class GoalUpdateView(LoginRequiredMixin, UpdateView):
    model = Goal
    form_class = GoalForm
    template_name = "core/goal_form.html"
    success_url = reverse_lazy("goal_list")

    def form_valid(self, form):
        messages.success(self.request, "Meta atualizada com sucesso!")
        return super().form_valid(form)

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)


class GoalDeleteView(LoginRequiredMixin, DeleteView):
    model = Goal
    template_name = "core/confirm_delete.html"
    success_url = reverse_lazy("goal_list")

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)


@login_required
def goal_deposit(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == "POST":
        form = GoalDepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            goal.current_amount += amount
            goal.save()
            messages.success(request, f'Aporte de R$ {amount:,.2f} registrado em "{goal.name}"!')
        else:
            messages.error(request, "Valor inválido para o aporte.")
    return redirect("goal_list")
