
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0010_shiftclose'),
    ]

    operations = [
        migrations.AddField(
            model_name='shiftclose',
            name='shift_started_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='ÐÐ°Ñ‡Ð°Ð»Ð¾ Ð½Ð° ÑÐ¼ÑÐ½Ð°'),
        ),
        migrations.AddField(
            model_name='shiftclose',
            name='sales_count',
            field=models.IntegerField(default=0, verbose_name='Ð‘Ñ€Ð¾Ð¹ Ð¿Ñ€Ð¾Ð´Ð°Ð¶Ð±Ð¸'),
        ),
        migrations.AddField(
            model_name='shiftclose',
            name='cash_transactions_count',
            field=models.IntegerField(default=0, verbose_name='Ð‘Ñ€Ð¾Ð¹ ÐºÐ°ÑÐ¾Ð²Ð¸ Ð´Ð²Ð¸Ð¶ÐµÐ½Ð¸Ñ'),
        ),
        migrations.AddField(
            model_name='shiftclose',
            name='report_data',
            field=models.JSONField(blank=True, default=dict, verbose_name='ÐŸÐ¾Ð´Ñ€Ð¾Ð±ÐµÐ½ Ð¾Ñ‚Ñ‡ÐµÑ‚'),
        ),
    ]
