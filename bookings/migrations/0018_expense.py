
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0017_alter_user_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=120, verbose_name='Ð Ð°Ð·Ñ…Ð¾Ð´')),
                ('category', models.CharField(choices=[('inventory', 'Ð”Ð¾ÑÑ‚Ð°Ð²ÐºÐ°'), ('utilities', 'ÐšÐ¾Ð½ÑÑƒÐ¼Ð°Ñ‚Ð¸Ð²Ð¸'), ('rent', 'ÐÐ°ÐµÐ¼'), ('maintenance', 'Ð ÐµÐ¼Ð¾Ð½Ñ‚'), ('salary', 'Ð—Ð°Ð¿Ð»Ð°Ñ‚Ð¸'), ('supplier', 'Ð”Ð¾ÑÑ‚Ð°Ð²Ñ‡Ð¸Ðº'), ('other', 'Ð”Ñ€ÑƒÐ³Ð¸')], default='other', max_length=20, verbose_name='ÐšÐ°Ñ‚ÐµÐ³Ð¾Ñ€Ð¸Ñ')),
                ('payment_method', models.CharField(choices=[('cash', 'Ð’ Ð±Ñ€Ð¾Ð¹'), ('card', 'Ð¡ ÐºÐ°Ñ€Ñ‚Ð°'), ('bank', 'Ð‘Ð°Ð½ÐºÐ¾Ð² Ð¿Ñ€ÐµÐ²Ð¾Ð´')], default='cash', max_length=10, verbose_name='ÐÐ°Ñ‡Ð¸Ð½ Ð½Ð° Ð¿Ð»Ð°Ñ‰Ð°Ð½Ðµ')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Ð¡ÑƒÐ¼Ð°')),
                ('comment', models.CharField(blank=True, default='', max_length=200, verbose_name='ÐšÐ¾Ð¼ÐµÐ½Ñ‚Ð°Ñ€')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Ð”Ð°Ñ‚Ð°')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Ð¡ÑŠÐ·Ð´Ð°Ð´ÐµÐ½Ð¾ Ð¾Ñ‚')),
            ],
        ),
    ]
