
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0008_alter_product_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='payment_method',
            field=models.CharField(choices=[('cash', 'Ð’ Ð±Ñ€Ð¾Ð¹'), ('card', 'Ð¡ ÐºÐ°Ñ€Ñ‚Ð°')], default='cash', max_length=10, verbose_name='ÐÐ°Ñ‡Ð¸Ð½ Ð½Ð° Ð¿Ð»Ð°Ñ‰Ð°Ð½Ðµ'),
        ),
        migrations.CreateModel(
            name='CashTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('in', 'Ð’Ð½Ð°ÑÑÐ½Ðµ'), ('out', 'Ð˜Ð·Ð²Ð°Ð¶Ð´Ð°Ð½Ðµ'), ('sale', 'ÐŸÑ€Ð¾Ð´Ð°Ð¶Ð±Ð° Ð² Ð±Ñ€Ð¾Ð¹')], max_length=10, verbose_name='Ð¢Ð¸Ð¿')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Ð¡ÑƒÐ¼Ð°')),
                ('comment', models.CharField(blank=True, default='', max_length=200, verbose_name='ÐšÐ¾Ð¼ÐµÐ½Ñ‚Ð°Ñ€')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Ð”Ð°Ñ‚Ð°')),
                ('cashier', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='ÐšÐ°ÑÐ¸ÐµÑ€')),
                ('sale', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='bookings.sale', verbose_name='ÐŸÑ€Ð¾Ð´Ð°Ð¶Ð±Ð°')),
            ],
        ),
    ]
