from django.core.management.base import BaseCommand

from bookings.models import TrainerProfile, User


TRAINERS = [
    {
        "username": "trainer_martin_petrov",
        "first_name": "Мартин",
        "last_name": "Петров",
        "expertise_level": "Старши треньор по техника, скорост и тактика.",
        "achievements": (
            "Многократен медалист от национални турнири. Финалист в държавно "
            "първенство на двойки. Над 8 години опит в подготовката на "
            "начинаещи и напреднали състезатели."
        ),
        "schedule_days": "Понеделник, сряда и петък: 17:00 - 21:00",
    },
    {
        "username": "trainer_elena_georgieva",
        "first_name": "Елена",
        "last_name": "Георгиева",
        "expertise_level": "Треньор за деца и любители, с фокус върху основите.",
        "achievements": (
            "Бивша състезателка в национални клубни турнири. Носител "
            "на отличия от регионални състезания. Работи с групи за начинаещи "
            "и индивидуални тренировки."
        ),
        "schedule_days": "Вторник и четвъртък: 16:00 - 20:00; събота: 10:00 - 14:00",
    },
]


class Command(BaseCommand):
    help = "Create or update the default trainer profiles for the home page."

    def handle(self, *args, **options):
        for trainer in TRAINERS:
            user, _ = User.objects.get_or_create(username=trainer["username"])
            user.first_name = trainer["first_name"]
            user.last_name = trainer["last_name"]
            user.email = f"{trainer['username']}@badminton.local"
            user.role = "trainer"
            user.is_active = False
            user.set_unusable_password()
            user.save()

            TrainerProfile.objects.update_or_create(
                user=user,
                defaults={
                    "expertise_level": trainer["expertise_level"],
                    "achievements": trainer["achievements"],
                    "schedule_days": trainer["schedule_days"],
                    "photo": "",
                },
            )

        self.stdout.write(self.style.SUCCESS("Default trainers are ready."))
