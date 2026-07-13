from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from billing.models import Brand, ProductGroup, Product, Customer, Invoice, CustomerProfile
from pagos.models import CobroFactura

class CobroFacturaTests(TestCase):
    def setUp(self):
        # Create dependencies for tests
        self.brand = Brand.objects.create(name="Test Brand")
        self.group = ProductGroup.objects.create(name="Test Group")
        self.product = Product.objects.create(
            name="Test Product",
            brand=self.brand,
            group=self.group,
            unit_price=Decimal("100.00"),
            stock=10
        )
        self.customer = Customer.objects.create(
            dni="1726354890",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        self.profile = CustomerProfile.objects.create(
            customer=self.customer,
            taxpayer_type="final",
            payment_terms="credit_30",
            credit_limit=Decimal("500.00")
        )

    def test_invoice_creation_initialization(self):
        """Test that invoices initialize their tipo_pago, saldo, and estado correctly on save."""
        # 1. Credit invoice
        inv_credit = Invoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("200.00"),
            tax=Decimal("30.00"),
            total=Decimal("230.00"),
            tipo_pago="CREDITO",
            is_active=True
        )
        self.assertEqual(inv_credit.saldo, Decimal("230.00"))
        self.assertEqual(inv_credit.estado, "PENDIENTE")
        self.assertTrue(inv_credit.numero.startswith("FAC-"))

        # 2. Cash invoice
        inv_cash = Invoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            tax=Decimal("15.00"),
            total=Decimal("115.00"),
            tipo_pago="CONTADO",
            is_active=True
        )
        self.assertEqual(inv_cash.saldo, Decimal("0.00"))
        self.assertEqual(inv_cash.estado, "PAGADA")

    def test_register_valid_payment(self):
        """Test registering a valid payment on a credit invoice."""
        invoice = Invoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("200.00"),
            tax=Decimal("30.00"),
            total=Decimal("230.00"),
            tipo_pago="CREDITO",
            is_active=True
        )
        
        # Register a payment of 100
        payment = CobroFactura.objects.create(
            factura=invoice,
            fecha=timezone.localtime(),
            valor=Decimal("100.00"),
            observacion="Abono inicial"
        )
        
        # Refresh invoice from DB
        invoice.refresh_from_db()
        self.assertEqual(invoice.saldo, Decimal("130.00"))
        self.assertEqual(invoice.estado, "PENDIENTE")

    def test_payment_value_validation(self):
        """Test that payments <= 0 are rejected."""
        invoice = Invoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("200.00"),
            tax=Decimal("30.00"),
            total=Decimal("230.00"),
            tipo_pago="CREDITO",
            is_active=True
        )
        
        # Negative payment
        payment_neg = CobroFactura(
            factura=invoice,
            fecha=timezone.localtime(),
            valor=Decimal("-50.00")
        )
        with self.assertRaises(ValidationError):
            payment_neg.save()

        # Zero payment
        payment_zero = CobroFactura(
            factura=invoice,
            fecha=timezone.localtime(),
            valor=Decimal("0.00")
        )
        with self.assertRaises(ValidationError):
            payment_zero.save()

    def test_payment_date_validation(self):
        """Test that payments with a date in the past are rejected."""
        invoice = Invoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            tax=Decimal("15.00"),
            total=Decimal("115.00"),
            tipo_pago="CREDITO",
            is_active=True
        )
        
        # Date in the past
        past_date = timezone.localtime() - timezone.timedelta(days=1)
        payment_past = CobroFactura(
            factura=invoice,
            fecha=past_date,
            valor=Decimal("50.00")
        )
        with self.assertRaises(ValidationError):
            payment_past.save()

    def test_payment_exceeding_balance_validation(self):
        """Test that payments exceeding the outstanding balance are rejected."""
        invoice = Invoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            tax=Decimal("15.00"),
            total=Decimal("115.00"),
            tipo_pago="CREDITO",
            is_active=True
        )
        
        # Pay more than 115
        payment_excess = CobroFactura(
            factura=invoice,
            fecha=timezone.localtime(),
            valor=Decimal("120.00")
        )
        with self.assertRaises(ValidationError):
            payment_excess.save()

    def test_payment_on_inactive_invoice_validation(self):
        """Test that payments on inactive/voided invoices are rejected."""
        invoice = Invoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            tax=Decimal("15.00"),
            total=Decimal("115.00"),
            tipo_pago="CREDITO",
            is_active=False # Inactive / voided
        )
        
        payment = CobroFactura(
            factura=invoice,
            fecha=timezone.localtime(),
            valor=Decimal("50.00")
        )
        with self.assertRaises(ValidationError):
            payment.save()

    def test_payment_fully_paid_transition(self):
        """Test that an invoice transitions to PAGADA when its balance reaches 0."""
        invoice = Invoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            tax=Decimal("15.00"),
            total=Decimal("115.00"),
            tipo_pago="CREDITO",
            is_active=True
        )
        
        # Pay 115 in full
        CobroFactura.objects.create(
            factura=invoice,
            fecha=timezone.localtime(),
            valor=Decimal("115.00")
        )
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.saldo, Decimal("0.00"))
        self.assertEqual(invoice.estado, "PAGADA")

    def test_edit_payment(self):
        """Test editing a payment updates the invoice balance and state correctly."""
        invoice = Invoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            tax=Decimal("15.00"),
            total=Decimal("115.00"),
            tipo_pago="CREDITO",
            is_active=True
        )
        
        payment = CobroFactura.objects.create(
            factura=invoice,
            fecha=timezone.localtime(),
            valor=Decimal("50.00")
        )
        
        # Verify initial payment state
        invoice.refresh_from_db()
        self.assertEqual(invoice.saldo, Decimal("65.00"))
        
        # Edit payment to 70.00
        payment.valor = Decimal("70.00")
        payment.save()
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.saldo, Decimal("45.00"))
        self.assertEqual(invoice.estado, "PENDIENTE")

        # Edit payment to 115.00 (fully paid)
        payment.valor = Decimal("115.00")
        payment.save()
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.saldo, Decimal("0.00"))
        self.assertEqual(invoice.estado, "PAGADA")

        # Edit payment back to 30.00 (reverts to PENDIENTE)
        payment.valor = Decimal("30.00")
        payment.save()
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.saldo, Decimal("85.00"))
        self.assertEqual(invoice.estado, "PENDIENTE")

    def test_delete_payment(self):
        """Test deleting a payment and reverting invoice balance."""
        invoice = Invoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            tax=Decimal("15.00"),
            total=Decimal("115.00"),
            tipo_pago="CREDITO",
            is_active=True
        )
        
        payment = CobroFactura.objects.create(
            factura=invoice,
            fecha=timezone.localtime(),
            valor=Decimal("50.00")
        )
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.saldo, Decimal("65.00"))
        
        # Delete the payment
        payment.delete()
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.saldo, Decimal("115.00"))
        self.assertEqual(invoice.estado, "PENDIENTE")

    def test_delete_payment_fully_paid_validation(self):
        """Test that deleting a payment from a fully paid invoice is rejected."""
        invoice = Invoice.objects.create(
            customer=self.customer,
            subtotal=Decimal("100.00"),
            tax=Decimal("15.00"),
            total=Decimal("115.00"),
            tipo_pago="CREDITO",
            is_active=True
        )
        
        payment = CobroFactura.objects.create(
            factura=invoice,
            fecha=timezone.localtime(),
            valor=Decimal("115.00")
        )
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.estado, "PAGADA")
        
        # Try to delete payment when invoice is fully paid
        with self.assertRaises(ValidationError):
            payment.delete()
