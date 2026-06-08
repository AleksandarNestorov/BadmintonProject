
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='booking',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='booking',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='product',
            name='stock_quantity',
        ),
        migrations.RemoveField(
            model_name='sale',
            name='sold_by',
        ),
        migrations.RemoveField(
            model_name='saleitem',
            name='price_at_moment',
        ),
        migrations.RemoveField(
            model_name='user',
            name='card_number',
        ),
        migrations.AddField(
            model_name='court',
            name='court_type',
            field=models.CharField(default='Ð¡Ñ‚Ð°Ð½Ð´Ð°Ñ€Ñ‚ÐµÐ½', max_length=50, verbose_name='ÐÐ°ÑÑ‚Ð¸Ð»ÐºÐ°'),
        ),
        migrations.AddField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='products/'),
        ),
        migrations.AddField(
            model_name='product',
            name='quantity',
            field=models.IntegerField(default=0, verbose_name='ÐÐ°Ð»Ð¸Ñ‡Ð½Ð¾ÑÑ‚'),
        ),
        migrations.AddField(
            model_name='sale',
            name='cashier',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='ÐšÐ°ÑÐ¸ÐµÑ€'),
        ),
        migrations.AddField(
            model_name='saleitem',
            name='price_at_sale',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='booking',
            name='court',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bookings.court'),
        ),
        migrations.AlterField(
            model_name='booking',
            name='customer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='booking',
            name='end_time',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='booking',
            name='payment_status',
            field=models.CharField(choices=[('not_paid', 'ÐÐµÐ¿Ð»Ð°Ñ‚ÐµÐ½Ð¾'), ('cash', 'ÐŸÐ»Ð°Ñ‚ÐµÐ½Ð¾ Ð² Ð±Ñ€Ð¾Ð¹'), ('card', 'ÐŸÐ»Ð°Ñ‚ÐµÐ½Ð¾ Ñ ÐºÐ°Ñ€Ñ‚Ð°')], default='not_paid', max_length=20),
        ),
        migrations.AlterField(
            model_name='booking',
            name='start_time',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='court',
            name='name',
            field=models.CharField(max_length=50, verbose_name='Ð˜Ð¼Ðµ Ð½Ð° ÐºÐ¾Ñ€Ñ‚Ð°'),
        ),
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.CharField(choices=[('service', 'Ð£ÑÐ»ÑƒÐ³Ð° (ÐÐ°ÐµÐ¼, ÐÐ°Ð¿Ð»Ð¸Ñ‚Ð°Ð½Ðµ)'), ('product', 'Ð¡Ñ‚Ð¾ÐºÐ° (Ð’Ð¾Ð´Ð°, Ð•ÐºÐ¸Ð¿Ð¸Ñ€Ð¾Ð²ÐºÐ°)')], default='product', max_length=20, verbose_name='ÐšÐ°Ñ‚ÐµÐ³Ð¾Ñ€Ð¸Ñ'),
        ),
        migrations.AlterField(
            model_name='product',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Ð˜Ð¼Ðµ'),
        ),
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(decimal_places=2, max_digits=6, verbose_name='Ð¦ÐµÐ½Ð°'),
        ),
        migrations.AlterField(
            model_name='sale',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Ð”Ð°Ñ‚Ð° Ð½Ð° Ð¿Ñ€Ð¾Ð´Ð°Ð¶Ð±Ð°'),
        ),
        migrations.AlterField(
            model_name='sale',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='saleitem',
            name='quantity',
            field=models.IntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='saleitem',
            name='sale',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bookings.sale'),
        ),
        migrations.AlterField(
            model_name='trainerprofile',
            name='achievements',
            field=models.TextField(blank=True, verbose_name='ÐŸÐ¾ÑÑ‚Ð¸Ð¶ÐµÐ½Ð¸Ñ'),
        ),
        migrations.AlterField(
            model_name='trainerprofile',
            name='expertise_level',
            field=models.CharField(default='ÐŸÑ€Ð¾Ñ„ÐµÑÐ¸Ð¾Ð½Ð°Ð»ÐµÐ½ Ñ‚Ñ€ÐµÐ½ÑŒÐ¾Ñ€', max_length=100),
        ),
        migrations.AlterField(
            model_name='trainerprofile',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='trainers/'),
        ),
        migrations.AlterField(
            model_name='trainerprofile',
            name='schedule_days',
            field=models.CharField(default='ÐŸÐ¾ Ð´Ð¾Ð³Ð¾Ð²Ð°Ñ€ÑÐ½Ðµ', max_length=100),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='email address'),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('client', 'ÐšÐ»Ð¸ÐµÐ½Ñ‚'), ('employee', 'Ð¡Ð»ÑƒÐ¶Ð¸Ñ‚ÐµÐ»'), ('admin', 'ÐÐ´Ð¼Ð¸Ð½Ð¸ÑÑ‚Ñ€Ð°Ñ‚Ð¾Ñ€')], default='client', max_length=10),
        ),
    ]
