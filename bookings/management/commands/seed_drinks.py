from decimal import Decimal

from django.core.management.base import BaseCommand

from bookings.models import Product


CATALOG_PRODUCTS = [
    {"name": "Кафе еспресо", "category": "drink", "price": Decimal("1.50"), "quantity": None},
    {"name": "Капучино", "category": "drink", "price": Decimal("2.20"), "quantity": None},
    {"name": "Фреш портокал", "category": "drink", "price": Decimal("3.50"), "quantity": None},
    {"name": "Devin минерална вода 0.5 л", "category": "drink", "price": Decimal("1.20"), "quantity": 72},
    {"name": "Devin минерална вода 1 л", "category": "drink", "price": Decimal("1.80"), "quantity": 36},
    {"name": "Devin минерална вода 1.5 л", "category": "drink", "price": Decimal("2.20"), "quantity": 24},
    {"name": "Devin газирана вода 0.5 л", "category": "drink", "price": Decimal("1.40"), "quantity": 36},
    {"name": "San Benedetto студен чай лимон 0.5 л", "category": "drink", "price": Decimal("2.20"), "quantity": 24},
    {"name": "Red Bull енергийна напитка 250 мл", "category": "drink", "price": Decimal("3.20"), "quantity": 24},
    {"name": "Hell енергийна напитка 250 мл", "category": "drink", "price": Decimal("2.40"), "quantity": 24},
    {"name": "Isostar изотонична напитка 0.5 л", "category": "drink", "price": Decimal("3.00"), "quantity": 20},
    {"name": "Powerade Mountain Blast 0.5 л", "category": "drink", "price": Decimal("2.80"), "quantity": 20},
    {"name": "Vitamin Well Reload 0.5 л", "category": "drink", "price": Decimal("3.40"), "quantity": 18},
    {"name": "Cappy портокал 250 мл", "category": "drink", "price": Decimal("1.90"), "quantity": 24},
    {"name": "Coca-Cola Zero 330 мл", "category": "drink", "price": Decimal("2.00"), "quantity": 36},
    {"name": "Айрян", "category": "drink", "price": Decimal("1.50"), "quantity": 30},
    {"name": "Barebells протеинов шейк 330 мл", "category": "drink", "price": Decimal("4.20"), "quantity": 12},
    {"name": "Barebells протеинов бар", "category": "drink", "price": Decimal("3.20"), "quantity": 24},
    {"name": "Corny енергиен бар", "category": "drink", "price": Decimal("2.40"), "quantity": 24},
    {"name": "Банан", "category": "drink", "price": Decimal("1.00"), "quantity": 30},
    {"name": "Yonex Astrox 100 ZZ", "category": "product", "price": Decimal("219.00"), "quantity": 2},
    {"name": "Yonex Nanoflare 800 Pro", "category": "product", "price": Decimal("205.00"), "quantity": 2},
    {"name": "Yonex Arcsaber 11 Pro", "category": "product", "price": Decimal("199.00"), "quantity": 2},
    {"name": "Victor Thruster Ryuga II Pro", "category": "product", "price": Decimal("189.00"), "quantity": 2},
    {"name": "Li-Ning Axforce 90 Dragon Max", "category": "product", "price": Decimal("195.00"), "quantity": 2},
    {"name": "Yonex Nanoray Light 18i", "category": "product", "price": Decimal("49.00"), "quantity": 6},
    {"name": "Babolat Satelite Gravity 74", "category": "product", "price": Decimal("89.00"), "quantity": 4},
    {"name": "Yonex Aerosensa 30 пера 12 бр.", "category": "product", "price": Decimal("29.00"), "quantity": 12},
    {"name": "RSL Classic Tourney пера 12 бр.", "category": "product", "price": Decimal("26.00"), "quantity": 10},
    {"name": "Yonex Mavis 350 пера 6 бр.", "category": "product", "price": Decimal("12.00"), "quantity": 18},
    {"name": "Yonex Super Grap AC102", "category": "product", "price": Decimal("4.50"), "quantity": 40},
    {"name": "Victor GR262 хавлиен грип", "category": "product", "price": Decimal("5.00"), "quantity": 24},
    {"name": "Yonex BG65 корда", "category": "product", "price": Decimal("8.00"), "quantity": 20},
    {"name": "Yonex BG80 Power корда", "category": "product", "price": Decimal("10.00"), "quantity": 16},
    {"name": "Yonex Power Cushion 65 Z3 обувки", "category": "product", "price": Decimal("119.00"), "quantity": 6},
    {"name": "Victor A970 NitroLite обувки", "category": "product", "price": Decimal("105.00"), "quantity": 5},
    {"name": "Li-Ning Saga Lite III обувки", "category": "product", "price": Decimal("82.00"), "quantity": 6},
    {"name": "Yonex Team тениска", "category": "product", "price": Decimal("28.00"), "quantity": 18},
    {"name": "Victor унисекс тениска", "category": "product", "price": Decimal("25.00"), "quantity": 18},
    {"name": "Yonex спортни шорти", "category": "product", "price": Decimal("24.00"), "quantity": 14},
    {"name": "Yonex Pro Tournament Bag 92231W", "category": "product", "price": Decimal("79.00"), "quantity": 4},
    {"name": "Victor BR9213 сак за ракети", "category": "product", "price": Decimal("69.00"), "quantity": 4},
    {"name": "Yonex калъф за ракета", "category": "product", "price": Decimal("12.00"), "quantity": 10},
    {"name": "Yonex AC489 накитници", "category": "product", "price": Decimal("8.00"), "quantity": 18},
    {"name": "Yonex 19122 спортни чорапи", "category": "product", "price": Decimal("7.00"), "quantity": 24},
    {"name": "Victor микрофибърна кърпа", "category": "product", "price": Decimal("9.00"), "quantity": 14},
]


def get_product_description(name, category):
    lower_name = name.lower()

    if category == "drink":
        if "кафе" in lower_name or "капучино" in lower_name:
            return "Топла напитка от минибара; продава се без складова бройка."
        if "фреш" in lower_name:
            return "Прясно изцеден сок; продава се без складова бройка."
        if "вода" in lower_name:
            return "Бутилирана вода за играчи и посетители."
        if "енергийна" in lower_name or "red bull" in lower_name or "hell" in lower_name:
            return "Енергийна напитка преди или след тренировка."
        if "изотонична" in lower_name or "powerade" in lower_name or "isostar" in lower_name:
            return "Спортна напитка за хидратация по време на игра."
        if "протеин" in lower_name or "barebells" in lower_name:
            return "Високопротеинов продукт за възстановяване след тренировка."
        if "бар" in lower_name or "банан" in lower_name:
            return "Бърза закуска за енергия преди или след игра."
        return "Напитка или храна от минибара."

    if "astrox" in lower_name:
        return "Атакуваща ракета за силна игра и мощен смаш."
    if "nanoflare" in lower_name:
        return "Лека и бърза ракета за защита и скорост."
    if "arcsaber" in lower_name:
        return "Контролна ракета за прецизни удари и стабилност."
    if "thruster" in lower_name or "axforce" in lower_name:
        return "Професионална ракета за мощна офанзивна игра."
    if "nanoray" in lower_name or "satelite" in lower_name:
        return "Лека ракета, подходяща за начинаещи и любители."
    if "пера" in lower_name or "mavis" in lower_name or "aerosensa" in lower_name:
        return "Комплект пера за игра; проверете вида преди продажба."
    if "грип" in lower_name:
        return "Лента за дръжка на ракета за по-добър захват."
    if "корда" in lower_name:
        return "Корда за наплитане на ракета."
    if "обувки" in lower_name:
        return "Специализирани обувки за зала и бадминтон настилка."
    if "тениска" in lower_name:
        return "Спортна тениска за тренировка и игра."
    if "шорти" in lower_name:
        return "Спортни шорти за тренировка и игра."
    if "сак" in lower_name or "bag" in lower_name:
        return "Сак за ракети, обувки и бадминтон екипировка."
    if "калъф" in lower_name:
        return "Калъф за защита и пренасяне на ракета."
    if "накитници" in lower_name:
        return "Накитници за попиване на пот по време на игра."
    if "чорапи" in lower_name:
        return "Спортни чорапи за игра в зала."
    if "кърпа" in lower_name:
        return "Микрофибърна кърпа за тренировка."

    return "Бадминтон продукт от магазина."

LEGACY_PRODUCT_NAMES = [
    "Минерална вода",
    "Минерална вода 500 мл",
    "Газирана вода",
    "Студен чай",
    "Енергийна напитка",
    "Изотонична напитка",
    "Електролитна напитка",
    "Витаминозна вода",
    "Сок натурален 250 мл",
    "Безалкохолна напитка 330 мл",
    "Протеинов шейк",
    "Протеинов бар",
    "Енергиен бар",
    "Ракета за начинаещи",
    "Ракета за напреднали",
    "Професионална ракета",
    "Пера перушина 12 бр.",
    "Пера пластмасови 6 бр.",
    "Грип за ракета",
    "Хавлиен грип",
    "Корда за бадминтон",
    "Обувки за бадминтон",
    "Тениска за бадминтон",
    "Спортни шорти",
    "Сак за ракети",
    "Калъф за ракета",
    "Накитници",
    "Спортни чорапи",
    "Кърпа микрофибър",
]


class Command(BaseCommand):
    help = "Create or update default shop products."

    def handle(self, *args, **options):
        Product.objects.filter(name__in=LEGACY_PRODUCT_NAMES).delete()

        for product in CATALOG_PRODUCTS:
            Product.objects.update_or_create(
                name=product["name"],
                defaults={
                    "category": product["category"],
                    "description": product.get(
                        "description",
                        get_product_description(product["name"], product["category"]),
                    ),
                    "price": product["price"],
                    "quantity": product["quantity"],
                },
            )

        self.stdout.write(self.style.SUCCESS("Default shop products are ready."))
