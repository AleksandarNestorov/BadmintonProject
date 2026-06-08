
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0018_expense'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='cancellation_reason',
            field=models.TextField(blank=True, default='', verbose_name='ÐŸÑ€Ð¸Ñ‡Ð¸Ð½Ð° Ð·Ð° Ð¾Ñ‚Ð¼ÑÐ½Ð°'),
        ),
        migrations.AddField(
            model_name='booking',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='ÐžÑ‚Ð¼ÐµÐ½ÐµÐ½Ð° Ð½Ð°'),
        ),
        migrations.AddField(
            model_name='booking',
            name='cancelled_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cancelled_booking_actions', to=settings.AUTH_USER_MODEL, verbose_name='ÐžÑ‚Ð¼ÐµÐ½ÐµÐ½Ð° Ð¾Ñ‚'),
        ),
    ]
