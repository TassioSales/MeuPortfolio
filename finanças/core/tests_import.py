from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Transaction, Category
from django.core.files.uploadedfile import SimpleUploadedFile

class ImportTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        self.url = reverse('transaction_import')

    def test_import_with_categories(self):
        csv_content = (
            "Data,Descricao,Valor,Categoria\n"
            "2023-10-01,Salário,5000.00,Salário\n"
            "2023-10-05,Aluguel,-1500.00,Moradia\n"
            "2023-10-10,Uber,-25.90,Transporte"
        ).encode('utf-8')
        
        file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        
        response = self.client.post(self.url, {'file': file}, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Check transactions
        self.assertEqual(Transaction.objects.count(), 3)
        
        # Check categories created
        self.assertTrue(Category.objects.filter(name='Salário', type='RECEITA').exists())
        self.assertTrue(Category.objects.filter(name='Moradia', type='DESPESA').exists())
        self.assertTrue(Category.objects.filter(name='Transporte', type='DESPESA').exists())
        
        # Check transaction association
        tx_uber = Transaction.objects.get(description='Uber')
        self.assertEqual(tx_uber.category.name, 'Transporte')

    def test_import_without_categories(self):
        csv_content = (
            "Data,Descricao,Valor\n"
            "2023-10-01,Salário,5000.00\n"
        ).encode('utf-8')
        
        file = SimpleUploadedFile("test_simple.csv", csv_content, content_type="text/csv")
        
        response = self.client.post(self.url, {'file': file}, follow=True)
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(Transaction.objects.count(), 1)
        tx = Transaction.objects.first()
        self.assertIsNone(tx.category)
