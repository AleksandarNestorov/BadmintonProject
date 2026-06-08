
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0016_user_profile_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('customer', 'ÐšÐ»Ð¸ÐµÐ½Ñ‚'), ('trainer', 'Ð¢Ñ€ÐµÐ½ÑŒÐ¾Ñ€'), ('employee', 'Ð¡Ð»ÑƒÐ¶Ð¸Ñ‚ÐµÐ»'), ('accounting', 'Ð¡Ñ‡ÐµÑ‚Ð¾Ð²Ð¾Ð´ÑÑ‚Ð²Ð¾'), ('admin', 'ÐÐ´Ð¼Ð¸Ð½Ð¸ÑÑ‚Ñ€Ð°Ñ‚Ð¾Ñ€')], default='customer', max_length=10),
        ),
    ]
