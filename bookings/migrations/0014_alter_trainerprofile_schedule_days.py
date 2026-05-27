from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0013_unify_user_roles"),
    ]

    operations = [
        migrations.AlterField(
            model_name="trainerprofile",
            name="schedule_days",
            field=models.CharField(default="По договаряне", max_length=255),
        ),
    ]
