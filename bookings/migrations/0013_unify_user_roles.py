
from django.db import migrations, models


def migrate_user_roles(apps, schema_editor):
    User = apps.get_model('bookings', 'User')
    TrainerProfile = apps.get_model('bookings', 'TrainerProfile')

    User.objects.filter(role='client').update(role='customer')

    trainer_user_ids = TrainerProfile.objects.values_list('user_id', flat=True)
    User.objects.filter(id__in=trainer_user_ids).update(role='trainer')

    User.objects.filter(role='admin').update(is_staff=True)
    User.objects.exclude(role='admin').filter(is_superuser=False).update(is_staff=False)


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0012_make_admin_role_staff'),
    ]

    operations = [
        migrations.RunPython(migrate_user_roles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('customer', 'Customer'),
                    ('trainer', 'Trainer'),
                    ('employee', 'Employee'),
                    ('admin', 'Admin'),
                ],
                default='customer',
                max_length=10,
            ),
        ),
    ]
