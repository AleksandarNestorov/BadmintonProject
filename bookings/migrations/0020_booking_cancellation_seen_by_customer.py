from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0019_booking_cancellation_reason_booking_cancelled_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='cancellation_seen_by_customer',
            field=models.BooleanField(default=True, verbose_name='Видяна от клиента'),
        ),
    ]
