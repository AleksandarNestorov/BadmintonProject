from decimal import Decimal

from django.core.management.base import BaseCommand

from bookings.models import Product, TrainerProfile


BASE_SERVICES = [
    {
        "name": "Игра за 1 час",
        "category": "game",
        "price": Decimal("10.00"),
        "description": "Стандартна резервация на корт за 60 минути.",
    },
    {
        "name": "Игра за 1 час с Multisport",
        "category": "game",
        "price": Decimal("0.00"),
        "description": "Игра за 60 минути, покрита изцяло с Multisport карта.",
    },
    {
        "name": "Доплащане за 30 минути",
        "category": "game",
        "price": Decimal("5.00"),
        "description": "Удължаване на вече започната игра с още 30 минути.",
    },
    {
        "name": "Наплитане на ракета",
        "category": "stringing",
        "price": Decimal("10.00"),
        "description": "Услуга за наплитане на ракета; кордата се заплаща отделно.",
    },
    {
        "name": "Наплитане на ракета с корда Yonex BG65",
        "category": "stringing",
        "price": Decimal("18.00"),
        "description": "Пълна услуга: наплитане плюс корда Yonex BG65.",
    },
    {
        "name": "Смяна на грип",
        "category": "stringing",
        "price": Decimal("3.00"),
        "description": "Поставяне на нов грип върху дръжката на ракетата.",
    },
    {
        "name": "Детска тренировка с Multisport Kids",
        "category": "training",
        "price": Decimal("0.00"),
        "description": "Детска тренировка, покрита изцяло с Multisport Kids карта.",
    },
    {
        "name": "Наем на ракета",
        "category": "rental",
        "price": Decimal("3.00"),
        "description": "Временен наем на ракета за игра в залата.",
    },
    {
        "name": "Наем на перо",
        "category": "rental",
        "price": Decimal("1.00"),
        "description": "Перо за игра на място, когато клиентът няма собствено.",
    },
]


def build_training_services():
    services = []
    trainers = TrainerProfile.objects.select_related("user").order_by("user__first_name", "user__last_name")

    for trainer in trainers:
        trainer_name = trainer.user.get_full_name() or trainer.user.username
        services.extend([
            {
                "name": f"Детска тренировка с {trainer_name}",
                "category": "training",
                "price": Decimal("12.00"),
                "description": f"Групова тренировка за деца с треньор {trainer_name}.",
            },
            {
                "name": f"Любителска тренировка с {trainer_name}",
                "category": "training",
                "price": Decimal("15.00"),
                "description": f"Тренировка за начинаещи и любители с треньор {trainer_name}.",
            },
            {
                "name": f"Индивидуална тренировка с {trainer_name}",
                "category": "training",
                "price": Decimal("30.00"),
                "description": f"Индивидуално занимание с треньор {trainer_name}.",
            },
        ])

    return services


class Command(BaseCommand):
    help = "Create or update default reception services."

    def handle(self, *args, **options):
        for service in BASE_SERVICES + build_training_services():
            Product.objects.update_or_create(
                name=service["name"],
                defaults={
                    "category": service["category"],
                    "description": service["description"],
                    "price": service["price"],
                    "quantity": None,
                },
            )

        self.stdout.write(self.style.SUCCESS("Default services are ready."))
