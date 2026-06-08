
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0009_sale_payment_method_cashtransaction'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShiftClose',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('closed_at', models.DateTimeField(auto_now_add=True, verbose_name='Ð”Ð°Ñ‚Ð° Ð½Ð° Ð¿Ñ€Ð¸ÐºÐ»ÑŽÑ‡Ð²Ð°Ð½Ðµ')),
                ('sales_total', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='ÐžÐ±Ð¾Ñ€Ð¾Ñ‚')),
                ('cash_total', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Ð’ Ð±Ñ€Ð¾Ð¹')),
                ('card_total', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Ð¡ ÐºÐ°Ñ€Ñ‚Ð°')),
                ('cash_balance', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='ÐÐ°Ð»Ð¸Ñ‡Ð½Ð¾ÑÑ‚ ÐºÐ°ÑÐ°')),
                ('attendance', models.IntegerField(default=0, verbose_name='ÐŸÐ¾ÑÐµÑ‰Ð°ÐµÐ¼Ð¾ÑÑ‚')),
                ('comment', models.CharField(blank=True, default='', max_length=200, verbose_name='ÐšÐ¾Ð¼ÐµÐ½Ñ‚Ð°Ñ€')),
                ('cashier', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='ÐšÐ°ÑÐ¸ÐµÑ€')),
            ],
        ),
    ]
