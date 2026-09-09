from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category


class CategoryFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mara", password="pass12345")
        self.client.login(username="mara", password="pass12345")

        self.moradia = Category.objects.create(user=self.user, name="Moradia", type="DESPESA")
        self.aluguel = Category.objects.create(user=self.user, name="Aluguel", type="DESPESA", parent=self.moradia)
        self.condominio = Category.objects.create(user=self.user, name="Condomínio", type="DESPESA", parent=self.moradia)
        self.transporte = Category.objects.create(user=self.user, name="Transporte", type="DESPESA")
        self.salario = Category.objects.create(user=self.user, name="Salário", type="RECEITA")

        other_user = User.objects.create_user(username="bob", password="pass12345")
        self.other_category = Category.objects.create(user=other_user, name="Categoria do Bob", type="DESPESA")

    def test_no_filter_shows_only_own_categories(self):
        response = self.client.get(reverse("category_list"))
        categories = list(response.context["categories"])
        self.assertNotIn(self.other_category, categories)
        self.assertEqual(len(categories), 5)

    def test_search_filters_by_name(self):
        response = self.client.get(reverse("category_list"), {"search": "alug"})
        categories = list(response.context["categories"])
        self.assertEqual(categories, [self.aluguel])

    def test_type_filter(self):
        response = self.client.get(reverse("category_list"), {"type": "RECEITA"})
        categories = list(response.context["categories"])
        self.assertEqual(categories, [self.salario])

    def test_parent_none_shows_only_top_level(self):
        response = self.client.get(reverse("category_list"), {"parent": "none"})
        categories = set(response.context["categories"])
        self.assertEqual(categories, {self.moradia, self.transporte, self.salario})

    def test_parent_filter_shows_parent_and_its_subcategories(self):
        response = self.client.get(reverse("category_list"), {"parent": str(self.moradia.pk)})
        categories = set(response.context["categories"])
        self.assertEqual(categories, {self.moradia, self.aluguel, self.condominio})

    def test_parent_dropdown_only_lists_top_level_categories(self):
        response = self.client.get(reverse("category_list"))
        parent_options = set(response.context["parent_categories"])
        self.assertEqual(parent_options, {self.moradia, self.transporte, self.salario})
