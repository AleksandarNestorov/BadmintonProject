from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0020_booking_cancellation_seen_by_customer'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Активен'),
        ),
    ]
