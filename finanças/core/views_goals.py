"""Goal CRUD views."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import GoalForm
from .models import Goal


class GoalListView(LoginRequiredMixin, ListView):
    model = Goal
    template_name = "core/goal_list.html"
    context_object_name = "goals"

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)


class GoalCreateView(LoginRequiredMixin, CreateView):
    model = Goal
    form_class = GoalForm
    template_name = "core/form.html"
    success_url = reverse_lazy("goal_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Meta criada com sucesso!")
        return super().form_valid(form)


class GoalUpdateView(LoginRequiredMixin, UpdateView):
    model = Goal
    form_class = GoalForm
    template_name = "core/form.html"
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
