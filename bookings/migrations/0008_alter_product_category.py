
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0007_alter_product_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.CharField(choices=[('drink', 'ÐÐ°Ð¿Ð¸Ñ‚ÐºÐ°/Ð¥Ñ€Ð°Ð½Ð°'), ('game', 'Ð˜Ð³Ñ€Ð°'), ('rental', 'ÐÐ°ÐµÐ¼'), ('stringing', 'ÐÐ°Ð¿Ð»Ð¸Ñ‚Ð°Ð½Ðµ'), ('training', 'Ð¢Ñ€ÐµÐ½Ð¸Ñ€Ð¾Ð²ÐºÐ°'), ('product', 'Ð¡Ñ‚Ð¾ÐºÐ°')], default='product', max_length=20, verbose_name='ÐšÐ°Ñ‚ÐµÐ³Ð¾Ñ€Ð¸Ñ'),
        ),
    ]
