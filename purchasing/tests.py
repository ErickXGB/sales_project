from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

class PurchaseFormTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username='testuser', password='password123')
        # Add the user to the required group and assign permissions so the view allows access
        from django.contrib.auth.models import Group, Permission
        group, _ = Group.objects.get_or_create(name='Compras')
        
        try:
            add_perm = Permission.objects.get(codename='add_purchase')
            view_perm = Permission.objects.get(codename='view_purchase')
            group.permissions.add(add_perm, view_perm)
        except Permission.DoesNotExist:
            pass
            
        self.user.groups.add(group)

    def test_purchase_create_requires_login(self):
        # Accessing the purchase create page without login should redirect to login page
        response = self.client.get(reverse('purchasing:purchase_create'))
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('login', response.url)

    def test_purchase_create_renders_cost_input(self):
        # Log in the user
        self.client.login(username='testuser', password='password123')
        
        # Access the page
        response = self.client.get(reverse('purchasing:purchase_create'))
        self.assertEqual(response.status_code, 200)
        
        # Verify that the unit_cost[] input is rendered and editable (no readonly)
        response_content = response.content.decode('utf-8')
        self.assertIn('name="unit_cost[]"', response_content)
        self.assertNotIn('name="unit_cost[]" readonly', response_content)
        self.assertIn('class="form-control cost-input"', response_content)
        self.assertIn('stock-info', response_content)
