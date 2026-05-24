from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. Потребител
class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('trainer', 'Trainer'),
        ('employee', 'Employee'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')

    def save(self, *args, **kwargs):
        if self.role == 'admin':
            self.is_staff = True
        elif not self.is_superuser:
            self.is_staff = False
        super().save(*args, **kwargs)

    def has_perm(self, perm, obj=None):
        if self.is_active and self.role == 'admin':
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if self.is_active and self.role == 'admin':
            return True
        return super().has_module_perms(app_label)

# 2. Треньор
class TrainerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='trainer_profile')
    expertise_level = models.CharField(max_length=100, default="Професионален треньор")
    achievements = models.TextField(blank=True, verbose_name="Постижения")
    schedule_days = models.CharField(max_length=100, default="По договаряне")
    photo = models.ImageField(upload_to='trainers/', blank=True, null=True)

    def __str__(self):
        return f"Треньор: {self.user.get_full_name()}"

# 3. Кортове
class Court(models.Model):
    name = models.CharField(max_length=50, verbose_name="Име на корта")
    court_type = models.CharField(max_length=50, default="Стандартен", verbose_name="Настилка")
    is_active = models.BooleanField(default=True, verbose_name="Активен ли е?")

    def __str__(self):
        return self.name

# 4. Продукти и Услуги
CATEGORY_CHOICES = (
    ('drink', 'Напитка/Храна'),
    ('game', 'Игра'),
    ('rental', 'Наем'),
    ('stringing', 'Наплитане'),
    ('training', 'Тренировка'),
    ('product', 'Стока'),
)

class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="Име")
    description = models.CharField(max_length=200, blank=True, default='', verbose_name="Пояснение")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='product', verbose_name="Категория")
    price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Цена")
    quantity = models.IntegerField(default=0, blank=True, null=True, verbose_name="Наличност") 
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.quantity} бр.)"

# 5. Резервации
class Booking(models.Model):
    court = models.ForeignKey(Court, on_delete=models.CASCADE)
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    PAYMENT_STATUS_CHOICES = (
        ('not_paid', 'Неплатено'),
        ('cash', 'Платено в брой'),
        ('card', 'Платено с карта'),
    )
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='not_paid')

    def __str__(self):
        return f"{self.court.name} - {self.start_time.strftime('%d.%m %H:%M')}"

# 6. Продажби (История на покупките от рецепцията) - ТОВА ЛИПСВАШЕ
class Sale(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'В брой'),
        ('card', 'С карта'),
    )

    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Касиер")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата на продажба")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='cash', verbose_name="Начин на плащане")

    def __str__(self):
        return f"Продажба #{self.id} от {self.created_at.strftime('%d.%m %H:%M')}"

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(default=1)
    price_at_sale = models.DecimalField(max_digits=6, decimal_places=2) # Цена в момента на продажбата

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class CashTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = (
        ('in', 'Внасяне'),
        ('out', 'Изваждане'),
        ('sale', 'Продажба в брой'),
    )

    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Касиер")
    sale = models.ForeignKey(Sale, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Продажба")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES, verbose_name="Тип")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сума")
    comment = models.CharField(max_length=200, blank=True, default='', verbose_name="Коментар")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.amount} €"


class ShiftClose(models.Model):
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Касиер")
    shift_started_at = models.DateTimeField(blank=True, null=True, verbose_name="Начало на смяна")
    closed_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата на приключване")
    sales_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Оборот")
    cash_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="В брой")
    card_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="С карта")
    cash_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Наличност каса")
    sales_count = models.IntegerField(default=0, verbose_name="Брой продажби")
    cash_transactions_count = models.IntegerField(default=0, verbose_name="Брой касови движения")
    attendance = models.IntegerField(default=0, verbose_name="Посещаемост")
    report_data = models.JSONField(blank=True, default=dict, verbose_name="Подробен отчет")
    comment = models.CharField(max_length=200, blank=True, default='', verbose_name="Коментар")

    def __str__(self):
        return f"Приключване #{self.id} - {self.closed_at.strftime('%d.%m.%Y %H:%M')}"
