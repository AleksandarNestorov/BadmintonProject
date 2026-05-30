from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0015_booking_trainer_and_training_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("male", "Мъж"), ("female", "Жена")],
                default="",
                max_length=10,
                verbose_name="Пол",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="profile_photo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="profiles/",
                verbose_name="Профилна снимка",
            ),
        ),
    ]
