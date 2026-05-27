from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0014_alter_trainerprofile_schedule_days"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="trainer",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"role": "trainer"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="trainer_bookings",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="training_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("amateur", "Любителска тренировка"),
                    ("individual", "Индивидуална тренировка"),
                ],
                default="",
                max_length=20,
            ),
        ),
    ]
