
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0002_remove_booking_created_at_remove_booking_created_by_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='quantity',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='ÐÐ°Ð»Ð¸Ñ‡Ð½Ð¾ÑÑ‚'),
        ),
    ]
