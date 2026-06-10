import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.views import LoginView
from .models import Product, TrainerProfile, Court, Booking, Sale, SaleItem, CashTransaction, ShiftClose, Expense, User
from .forms import (
    AdminCatalogItemForm,
    AdminUserManagementForm,
    CustomerProfileEditForm,
    ExpenseForm,
    ProfilePhotoForm,
    UserLoginForm,
    UserRegisterForm,
)
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta, time
from decimal import Decimal
from django.db import transaction
from django.db.models import Q, Sum, Value
from django.db.models.functions import Concat
from django.urls import reverse
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

BOOKING_GRACE_PERIOD = timedelta(minutes=30)
BOOKING_MAX_DAYS_AHEAD = 14
TRAINER_BOOKING_MAX_DAYS_AHEAD = 30
MAX_DAILY_BOOKINGS_PER_CUSTOMER = 6
BOOKING_TIME_ZONE = ZoneInfo('Europe/Sofia')
RECEPTION_BILL_SESSION_KEY = 'reception_bill'
RECEPTION_SERVICE_CATEGORIES = ['game', 'rental', 'stringing', 'training']
FINANCE_FILTER_CHOICES = [
    ('all', 'Всички'),
    ('drink', 'Напитки и храни'),
    ('product', 'Стоки'),
    ('game', 'Игра'),
    ('rental', 'Наем'),
    ('stringing', 'Наплитане'),
    ('training', 'Тренировка'),
]
TRAINING_TYPE_LABELS = {
    'amateur': 'Любителска тренировка',
    'individual': 'Индивидуална тренировка',
}
TRAINER_BOOKING_RULES = {
    'trainer_martin_petrov': [
        {
            'weekdays': {0, 2, 4},
            'hours': [19, 20],
            'training_types': ['amateur', 'individual'],
        },
    ],
    'trainer_elena_georgieva': [
        {
            'weekdays': {1, 3},
            'hours': [18, 19],
            'training_types': ['amateur', 'individual'],
        },
        {
            'weekdays': {5},
            'hours': [10, 11, 12, 13],
            'training_types': ['amateur'],
        },
    ],
}


def get_slot_start(selected_date, hour):
    slot_start = datetime.combine(selected_date, time(hour, 0))
    return timezone.make_aware(slot_start, timezone.get_current_timezone())


def get_booking_day_bounds(selected_date):
    day_start = timezone.make_aware(
        datetime.combine(selected_date, time.min),
        BOOKING_TIME_ZONE,
    )
    return day_start, day_start + timedelta(days=1)


def get_booking_local_start(booking):
    return timezone.localtime(booking.start_time, BOOKING_TIME_ZONE)


def is_slot_bookable(selected_date, hour):
    local_slot_start = datetime.combine(
        selected_date,
        time(hour, 0),
        tzinfo=BOOKING_TIME_ZONE,
    )
    return datetime.now(BOOKING_TIME_ZONE) < local_slot_start + BOOKING_GRACE_PERIOD


def get_booking_max_days_ahead(user=None):
    if user and getattr(user, 'is_authenticated', False) and getattr(user, 'role', '') == 'trainer':
        return TRAINER_BOOKING_MAX_DAYS_AHEAD
    return BOOKING_MAX_DAYS_AHEAD


def get_booking_date_bounds(user=None):
    today = timezone.localdate()
    return today, today + timedelta(days=get_booking_max_days_ahead(user))


def parse_schedule_date(date_str, user=None):
    min_date, max_date = get_booking_date_bounds(user)

    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = min_date
    else:
        selected_date = min_date

    if selected_date < min_date:
        return min_date, min_date, max_date, True
    if selected_date > max_date:
        return max_date, min_date, max_date, True

    return selected_date, min_date, max_date, False


def is_date_in_booking_window(selected_date, user=None):
    min_date, max_date = get_booking_date_bounds(user)
    return min_date <= selected_date <= max_date


def build_training_type_options(training_types):
    return [
        {
            'value': training_type,
            'label': TRAINING_TYPE_LABELS[training_type],
        }
        for training_type in training_types
        if training_type in TRAINING_TYPE_LABELS
    ]


def build_trainer_options_by_hour(selected_date):
    weekday = selected_date.weekday()
    trainers_by_username = {
        user.username: user
        for user in User.objects.filter(
            username__in=TRAINER_BOOKING_RULES.keys(),
            role='trainer',
            is_active=True,
        )
    }
    options_by_hour = {}

    for username, availability_rules in TRAINER_BOOKING_RULES.items():
        trainer = trainers_by_username.get(username)
        if not trainer:
            continue

        trainer_name = trainer.get_full_name() or trainer.username
        for rule in availability_rules:
            if weekday not in rule['weekdays']:
                continue

            trainer_option = {
                'id': trainer.id,
                'name': trainer_name,
                'training_types': build_training_type_options(rule['training_types']),
                'training_type_values': rule['training_types'],
            }

            for hour in rule['hours']:
                options_by_hour.setdefault(hour, []).append(trainer_option)

    return options_by_hour


def user_can_access_reception(user):
    return user.is_superuser or user.role in ['admin', 'employee']


def user_can_access_finance(user):
    return user.role == 'accounting'


def user_can_access_management(user):
    return user.is_superuser or user.role == 'admin'


def user_can_create_own_bookings(user):
    return getattr(user, 'is_authenticated', False) and getattr(user, 'role', '') in ['customer', 'trainer']


class RoleAwareLoginView(LoginView):
    template_name = 'login.html'
    authentication_form = UserLoginForm

    def get_success_url(self):
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        user_role = getattr(self.request.user, 'role', '')
        if user_role == 'accounting':
            return reverse('finance')
        if user_role == 'employee':
            return reverse('reception')
        if user_role == 'admin':
            return reverse('management')
        return reverse('home')


def get_reception_bill(request):
    return request.session.get(RECEPTION_BILL_SESSION_KEY, {})


def save_reception_bill(request, bill):
    request.session[RECEPTION_BILL_SESSION_KEY] = bill
    request.session.modified = True


def build_reception_bill_context(bill):
    product_ids = [int(product_id) for product_id in bill.keys()]
    products_by_id = Product.objects.in_bulk(product_ids)
    items = []
    total = Decimal('0.00')

    for product_id, quantity in bill.items():
        product = products_by_id.get(int(product_id))
        if not product:
            continue

        line_total = product.price * quantity
        total += line_total
        items.append({
            'product': product,
            'quantity': quantity,
            'line_total': line_total,
        })

    return {
        'items': items,
        'total': total,
        'count': sum(item['quantity'] for item in items),
    }


def get_report_periods():
    now = timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    current_month_start = today_start.replace(day=1)
    current_year_start = today_start.replace(month=1, day=1)
    return today_start, current_month_start, current_year_start


def get_month_bounds(year, month):
    now = timezone.localtime()
    start = now.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
    if month == 12:
        end = start.replace(year=year + 1, month=1)
    else:
        end = start.replace(month=month + 1)
    return start, end


def get_day_bounds(year, month, day):
    now = timezone.localtime()
    start = now.replace(year=year, month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def get_year_bounds(year):
    now = timezone.localtime()
    start = now.replace(year=year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(year=year + 1)
    return start, end


def money_sum(queryset, field='total_amount'):
    return queryset.aggregate(total=Sum(field))['total'] or Decimal('0.00')


def attendance_sum(start, end=None):
    attendance_filter = Q(product__name__in=['Игра за 1 час', 'Игра за 1 час с Multisport']) | Q(product__category='training')
    sale_item_filter = Q(sale__created_at__gte=start) & attendance_filter
    if end:
        sale_item_filter &= Q(sale__created_at__lt=end)

    return SaleItem.objects.filter(sale_item_filter).aggregate(total=Sum('quantity'))['total'] or 0


def money_text(value):
    return f"{(value or Decimal('0.00')):.2f}"


def signed_money_text(value):
    value = value or Decimal('0.00')
    return f"{value:.2f}"


def decimal_percent_change(current_value, previous_value):
    current_value = current_value or Decimal('0.00')
    previous_value = previous_value or Decimal('0.00')
    if previous_value == 0:
        if current_value == 0:
            return None
        return Decimal('100.00')
    return ((current_value - previous_value) / previous_value) * Decimal('100.00')


def build_comparison_data(current_value, previous_value):
    current_value = current_value or Decimal('0.00')
    previous_value = previous_value or Decimal('0.00')
    delta = current_value - previous_value
    percent = decimal_percent_change(current_value, previous_value)
    if delta > 0:
        direction = 'up'
        label = 'Ръст'
    elif delta < 0:
        direction = 'down'
        label = 'Спад'
    else:
        direction = 'same'
        label = 'Без промяна'

    return {
        'current': current_value,
        'previous': previous_value,
        'delta': delta,
        'percent': percent,
        'direction': direction,
        'label': label,
    }


def build_payment_breakdown(sales_queryset):
    cash_total = money_sum(sales_queryset.filter(payment_method='cash'))
    card_total = money_sum(sales_queryset.filter(payment_method='card'))
    cash_count = sales_queryset.filter(payment_method='cash').count()
    card_count = sales_queryset.filter(payment_method='card').count()
    total = cash_total + card_total

    return [
        {
            'key': 'cash',
            'label': 'В брой',
            'total': cash_total,
            'count': cash_count,
            'share': (cash_total / total * Decimal('100.00')) if total else Decimal('0.00'),
        },
        {
            'key': 'card',
            'label': 'С карта',
            'total': card_total,
            'count': card_count,
            'share': (card_total / total * Decimal('100.00')) if total else Decimal('0.00'),
        },
    ]


def get_previous_period_bounds(start, end):
    period_delta = end - start
    return start - period_delta, start


def get_finance_filter_value(request):
    selected_filter = request.GET.get('finance_type') or 'all'
    valid_values = {value for value, _ in FINANCE_FILTER_CHOICES}
    return selected_filter if selected_filter in valid_values else 'all'


def apply_finance_type_filter(queryset, selected_filter, field_name='category'):
    if selected_filter == 'all':
        return queryset
    return queryset.filter(**{field_name: selected_filter})


def summarize_sale_items(sales_queryset, categories=None, limit=5):
    items = (
        SaleItem.objects
        .filter(sale__in=sales_queryset)
        .select_related('product')
    )
    if categories is not None:
        items = items.filter(product__category__in=categories)

    summary = {}
    for item in items:
        product = item.product
        if not product:
            continue
        key = product.id
        entry = summary.setdefault(
            key,
            {
                'name': product.name,
                'category': product.category,
                'category_label': product.get_category_display(),
                'quantity': 0,
                'total': Decimal('0.00'),
            },
        )
        entry['quantity'] += item.quantity
        entry['total'] += item.quantity * item.price_at_sale

    results = sorted(
        summary.values(),
        key=lambda value: (value['quantity'], value['total']),
        reverse=True,
    )
    return results[:limit]


def build_top_trainers(start, end, limit=5):
    trainer_stats = {}
    bookings = (
        Booking.objects
        .filter(
            trainer__isnull=False,
            start_time__gte=start,
            start_time__lt=end,
            is_active=True,
        )
        .select_related('trainer')
    )
    for booking in bookings:
        trainer = booking.trainer
        if not trainer:
            continue
        key = trainer.id
        entry = trainer_stats.setdefault(
            key,
            {
                'name': trainer.get_full_name() or trainer.username,
                'bookings': 0,
                'individual': 0,
                'amateur': 0,
            },
        )
        entry['bookings'] += 1
        if booking.training_type == 'individual':
            entry['individual'] += 1
        elif booking.training_type == 'amateur':
            entry['amateur'] += 1

    return sorted(trainer_stats.values(), key=lambda value: value['bookings'], reverse=True)[:limit]


def build_best_month():
    first_sale = Sale.objects.order_by('created_at').first()
    if not first_sale:
        return None

    now = timezone.localtime()
    cursor = timezone.localtime(first_sale.created_at).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    best_month = None

    while cursor <= last_month:
        if cursor.month == 12:
            next_month = cursor.replace(year=cursor.year + 1, month=1)
        else:
            next_month = cursor.replace(month=cursor.month + 1)
        total = money_sum(Sale.objects.filter(created_at__gte=cursor, created_at__lt=next_month))
        if best_month is None or total > best_month['total']:
            best_month = {
                'label': cursor.strftime('%m.%Y'),
                'total': total,
            }
        cursor = next_month

    return best_month


def build_shift_report_snapshot(shift_start, end=None):
    end = end or timezone.now()
    sales = list(
        Sale.objects
        .filter(created_at__gte=shift_start, created_at__lt=end)
        .prefetch_related('saleitem_set__product')
        .order_by('-created_at')
    )
    cash_transactions = list(
        CashTransaction.objects
        .filter(created_at__gte=shift_start, created_at__lt=end)
        .order_by('-created_at')
    )
    expenses = list(
        Expense.objects
        .filter(created_at__gte=shift_start, created_at__lt=end)
        .select_related('created_by')
        .order_by('-created_at')
    )

    product_summary = {}
    service_summary = {}

    serialized_sales = []
    for sale in sales:
        serialized_items = []
        for item in sale.saleitem_set.all():
            product = item.product
            item_name = product.name if product else '\u0418\u0437\u0442\u0440\u0438\u0442 \u043f\u0440\u043e\u0434\u0443\u043a\u0442'
            category = product.category if product else ''
            category_label = product.get_category_display() if product else '-'
            line_total = item.price_at_sale * item.quantity
            serialized_items.append({
                'name': item_name,
                'category': category,
                'category_label': category_label,
                'quantity': item.quantity,
                'price': money_text(item.price_at_sale),
                'total': money_text(line_total),
            })

            summary_target = service_summary if category in RECEPTION_SERVICE_CATEGORIES else product_summary
            summary_key = f"{item_name}|{category}|{money_text(item.price_at_sale)}"
            if summary_key not in summary_target:
                summary_target[summary_key] = {
                    'name': item_name,
                    'category': category,
                    'category_label': category_label,
                    'quantity': 0,
                    'total_amount': Decimal('0.00'),
                }
            summary_target[summary_key]['quantity'] += item.quantity
            summary_target[summary_key]['total_amount'] += line_total

        serialized_sales.append({
            'id': sale.id,
            'time': timezone.localtime(sale.created_at).strftime('%d.%m.%Y %H:%M'),
            'payment_method': sale.get_payment_method_display(),
            'total': money_text(sale.total_amount),
            'items': serialized_items,
        })

    def serialize_summary(summary):
        return [
            {
                'name': item['name'],
                'category': item['category'],
                'category_label': item['category_label'],
                'quantity': item['quantity'],
                'total': money_text(item['total_amount']),
            }
            for item in sorted(summary.values(), key=lambda value: value['name'])
        ]

    cash_total = sum((sale.total_amount for sale in sales if sale.payment_method == 'cash'), Decimal('0.00'))
    card_total = sum((sale.total_amount for sale in sales if sale.payment_method == 'card'), Decimal('0.00'))
    sales_total = cash_total + card_total
    expense_total = sum((item.amount for item in expenses), Decimal('0.00'))
    profit_total = sales_total - expense_total
    cash_balance = sum((item.amount for item in cash_transactions), Decimal('0.00'))

    return {
        'period': {
            'start': timezone.localtime(shift_start).strftime('%d.%m.%Y %H:%M'),
            'end': timezone.localtime(end).strftime('%d.%m.%Y %H:%M'),
        },
        'totals': {
            'sales_total': money_text(sales_total),
            'cash_total': money_text(cash_total),
            'card_total': money_text(card_total),
            'expense_total': money_text(expense_total),
            'profit_total': money_text(profit_total),
            'cash_balance': money_text(cash_balance),
        },
        'sales_count': len(sales),
        'expenses_count': len(expenses),
        'cash_transactions_count': len(cash_transactions),
        'attendance': attendance_sum(shift_start, end),
        'sales': serialized_sales,
        'product_summary': serialize_summary(product_summary),
        'service_summary': serialize_summary(service_summary),
        'expenses': [
            {
                'time': timezone.localtime(item.created_at).strftime('%d.%m.%Y %H:%M'),
                'title': item.title,
                'category': item.get_category_display(),
                'payment_method': item.get_payment_method_display(),
                'amount': money_text(item.amount),
                'comment': item.comment or '-',
            }
            for item in expenses
        ],
        'cash_transactions': [
            {
                'time': timezone.localtime(item.created_at).strftime('%d.%m.%Y %H:%M'),
                'type': item.get_transaction_type_display(),
                'amount': money_text(item.amount),
                'comment': item.comment or '-',
            }
            for item in cash_transactions
        ],
    }

def get_current_shift_start(today_start):
    last_close = ShiftClose.objects.filter(closed_at__gte=today_start).order_by('-closed_at').first()
    return last_close.closed_at if last_close else today_start


def has_reception_activity_since_last_close(today_start):
    shift_start = get_current_shift_start(today_start)
    has_sales = Sale.objects.filter(created_at__gte=shift_start).exists()
    has_cash_transactions = CashTransaction.objects.filter(created_at__gte=shift_start).exists()
    has_expenses = Expense.objects.filter(created_at__gte=shift_start).exists()
    return has_sales or has_cash_transactions or has_expenses


def build_reception_reports_context(request):
    today_start, current_month_start, current_year_start = get_report_periods()
    selected_day_value = request.GET.get('report_date') or today_start.strftime('%Y-%m-%d')
    selected_month_value = request.GET.get('report_month') or current_month_start.strftime('%Y-%m')
    selected_year_value = request.GET.get('report_year') or str(current_year_start.year)
    selected_archive_value = request.GET.get('archive_date') or ''
    selected_finance_filter = get_finance_filter_value(request)

    try:
        selected_day_year, selected_day_month, selected_day = [int(part) for part in selected_day_value.split('-')]
        day_start, day_end = get_day_bounds(selected_day_year, selected_day_month, selected_day)
    except (TypeError, ValueError):
        day_start, day_end = today_start, today_start + timedelta(days=1)
        selected_day_value = today_start.strftime('%Y-%m-%d')

    try:
        selected_month_year, selected_month = [int(part) for part in selected_month_value.split('-')]
        month_start, month_end = get_month_bounds(selected_month_year, selected_month)
    except (TypeError, ValueError):
        month_start = current_month_start
        month_end = get_month_bounds(current_month_start.year, current_month_start.month)[1]
        selected_month_value = current_month_start.strftime('%Y-%m')

    try:
        selected_year = int(selected_year_value)
        year_start, year_end = get_year_bounds(selected_year)
    except (TypeError, ValueError):
        year_start = current_year_start
        year_end = get_year_bounds(current_year_start.year)[1]
        selected_year = current_year_start.year

    first_sale = Sale.objects.order_by('created_at').first()
    first_expense = Expense.objects.order_by('created_at').first()
    first_record = first_sale or first_expense
    if first_sale and first_expense:
        first_record = first_sale if first_sale.created_at <= first_expense.created_at else first_expense
    first_year = timezone.localtime(first_record.created_at).year if first_record else current_year_start.year
    report_years = range(current_year_start.year, first_year - 1, -1)

    shift_start = get_current_shift_start(today_start)
    if day_start.date() == today_start.date():
        daily_start = shift_start
    else:
        daily_start = day_start

    daily_sales_queryset = Sale.objects.filter(created_at__gte=daily_start, created_at__lt=day_end)
    current_shift_sales = Sale.objects.filter(created_at__gte=shift_start)
    month_sales = Sale.objects.filter(created_at__gte=month_start, created_at__lt=month_end)
    year_sales = Sale.objects.filter(created_at__gte=year_start, created_at__lt=year_end)
    daily_cash_transactions = CashTransaction.objects.filter(created_at__gte=daily_start, created_at__lt=day_end)
    current_cash_transactions = CashTransaction.objects.filter(created_at__gte=shift_start)
    daily_expenses_queryset = Expense.objects.filter(created_at__gte=daily_start, created_at__lt=day_end)
    current_shift_expenses_queryset = Expense.objects.filter(created_at__gte=shift_start)
    month_expenses = Expense.objects.filter(created_at__gte=month_start, created_at__lt=month_end)
    year_expenses = Expense.objects.filter(created_at__gte=year_start, created_at__lt=year_end)
    daily_sales = list(daily_sales_queryset.prefetch_related('saleitem_set__product').order_by('-created_at'))
    current_shift_report = build_shift_report_snapshot(shift_start)

    previous_day_start, previous_day_end = get_previous_period_bounds(day_start, day_end)
    previous_month_start, previous_month_end = get_previous_period_bounds(month_start, month_end)
    previous_year_start, previous_year_end = get_previous_period_bounds(year_start, year_end)

    daily_sales_total = money_sum(daily_sales_queryset)
    daily_expense_total = money_sum(daily_expenses_queryset, 'amount')
    month_sales_total = money_sum(month_sales)
    month_expense_total = money_sum(month_expenses, 'amount')
    year_sales_total = money_sum(year_sales)
    year_expense_total = money_sum(year_expenses, 'amount')
    current_sales_total = money_sum(current_shift_sales)
    current_expense_total = money_sum(current_shift_expenses_queryset, 'amount')

    previous_day_sales_total = money_sum(Sale.objects.filter(created_at__gte=previous_day_start, created_at__lt=previous_day_end))
    previous_day_expense_total = money_sum(Expense.objects.filter(created_at__gte=previous_day_start, created_at__lt=previous_day_end), 'amount')
    previous_month_sales_total = money_sum(Sale.objects.filter(created_at__gte=previous_month_start, created_at__lt=previous_month_end))
    previous_month_expense_total = money_sum(Expense.objects.filter(created_at__gte=previous_month_start, created_at__lt=previous_month_end), 'amount')
    previous_year_sales_total = money_sum(Sale.objects.filter(created_at__gte=previous_year_start, created_at__lt=previous_year_end))
    previous_year_expense_total = money_sum(Expense.objects.filter(created_at__gte=previous_year_start, created_at__lt=previous_year_end), 'amount')

    archive_is_filtered = False
    selected_archive_label = '\u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0442\u0435 30 \u043f\u0440\u0438\u043a\u043b\u044e\u0447\u0432\u0430\u043d\u0438\u044f'
    shift_close_archive_queryset = ShiftClose.objects.order_by('-closed_at')
    if selected_archive_value:
        try:
            archive_year, archive_month, archive_day = [int(part) for part in selected_archive_value.split('-')]
            archive_start, archive_end = get_day_bounds(archive_year, archive_month, archive_day)
            shift_close_archive_queryset = shift_close_archive_queryset.filter(closed_at__gte=archive_start, closed_at__lt=archive_end)
            selected_archive_label = archive_start.strftime('%d.%m.%Y')
            archive_is_filtered = True
        except (TypeError, ValueError):
            selected_archive_value = ''

    shift_close_archive = shift_close_archive_queryset[:30]
    low_stock_products = Product.objects.filter(is_active=True, quantity__isnull=False, quantity__lte=5).exclude(category__in=RECEPTION_SERVICE_CATEGORIES).order_by('quantity', 'name')

    filtered_products_queryset = apply_finance_type_filter(
        Product.objects.filter(is_active=True).exclude(category__in=RECEPTION_SERVICE_CATEGORIES).order_by('category', 'name'),
        selected_finance_filter,
    )
    filtered_services_queryset = apply_finance_type_filter(
        Product.objects.filter(is_active=True, category__in=RECEPTION_SERVICE_CATEGORIES).order_by('category', 'name'),
        selected_finance_filter,
    )
    filtered_sales_history = (
        Sale.objects
        .select_related('cashier')
        .prefetch_related('saleitem_set__product')
        .order_by('-created_at')
    )
    if selected_finance_filter != 'all':
        filtered_sales_history = filtered_sales_history.filter(saleitem__product__category=selected_finance_filter).distinct()

    strongest_month = build_best_month()
    month_top_products = summarize_sale_items(month_sales, categories=['drink', 'product'], limit=5)
    month_top_services = summarize_sale_items(month_sales, categories=RECEPTION_SERVICE_CATEGORIES, limit=5)
    month_top_trainers = build_top_trainers(month_start, month_end, limit=5)

    return {
        'cash_balance': money_sum(current_cash_transactions, 'amount'),
        'current_sales_total': current_sales_total,
        'current_expense_total': current_expense_total,
        'current_profit_total': current_sales_total - current_expense_total,
        'current_card_sales_total': money_sum(current_shift_sales.filter(payment_method='card')),
        'today_sales_total': daily_sales_total,
        'today_expense_total': daily_expense_total,
        'today_profit_total': daily_sales_total - daily_expense_total,
        'today_cash_sales_total': money_sum(daily_sales_queryset.filter(payment_method='cash')),
        'today_card_sales_total': money_sum(daily_sales_queryset.filter(payment_method='card')),
        'today_sales_count': daily_sales_queryset.count(),
        'today_attendance': attendance_sum(daily_start, day_end),
        'daily_cash_balance': money_sum(daily_cash_transactions, 'amount'),
        'daily_payment_breakdown': build_payment_breakdown(daily_sales_queryset),
        'daily_sales_comparison': build_comparison_data(daily_sales_total, previous_day_sales_total),
        'daily_expense_comparison': build_comparison_data(daily_expense_total, previous_day_expense_total),
        'daily_profit_comparison': build_comparison_data(daily_sales_total - daily_expense_total, previous_day_sales_total - previous_day_expense_total),
        'selected_day_value': selected_day_value,
        'selected_day_label': day_start.strftime('%d.%m.%Y'),
        'current_shift_start': shift_start,
        'month_sales_total': month_sales_total,
        'month_expense_total': month_expense_total,
        'month_profit_total': month_sales_total - month_expense_total,
        'month_sales_count': month_sales.count(),
        'month_attendance': attendance_sum(month_start, month_end),
        'month_payment_breakdown': build_payment_breakdown(month_sales),
        'month_sales_comparison': build_comparison_data(month_sales_total, previous_month_sales_total),
        'month_expense_comparison': build_comparison_data(month_expense_total, previous_month_expense_total),
        'month_profit_comparison': build_comparison_data(month_sales_total - month_expense_total, previous_month_sales_total - previous_month_expense_total),
        'selected_month_value': selected_month_value,
        'selected_month_label': month_start.strftime('%m.%Y'),
        'year_sales_total': year_sales_total,
        'year_expense_total': year_expense_total,
        'year_profit_total': year_sales_total - year_expense_total,
        'year_sales_count': year_sales.count(),
        'year_attendance': attendance_sum(year_start, year_end),
        'year_payment_breakdown': build_payment_breakdown(year_sales),
        'year_sales_comparison': build_comparison_data(year_sales_total, previous_year_sales_total),
        'year_expense_comparison': build_comparison_data(year_expense_total, previous_year_expense_total),
        'year_profit_comparison': build_comparison_data(year_sales_total - year_expense_total, previous_year_sales_total - previous_year_expense_total),
        'selected_year': selected_year,
        'report_years': report_years,
        'recent_sales': daily_sales[:5],
        'daily_sales': daily_sales,
        'daily_sales_has_more': len(daily_sales) > 5,
        'cash_transactions': current_cash_transactions.order_by('-created_at')[:20],
        'current_shift_expenses': current_shift_expenses_queryset.order_by('-created_at')[:15],
        'recent_expenses': Expense.objects.select_related('created_by').order_by('-created_at')[:15],
        'recent_shift_closes': ShiftClose.objects.filter(closed_at__gte=day_start, closed_at__lt=day_end).order_by('-closed_at'),
        'current_shift_report': current_shift_report,
        'shift_close_archive': shift_close_archive,
        'selected_archive_value': selected_archive_value,
        'selected_archive_label': selected_archive_label,
        'archive_is_filtered': archive_is_filtered,
        'selected_finance_filter': selected_finance_filter,
        'finance_filter_choices': FINANCE_FILTER_CHOICES,
        'filtered_sales_history': filtered_sales_history[:15],
        'filtered_products': filtered_products_queryset,
        'filtered_services': filtered_services_queryset,
        'low_stock_products': low_stock_products,
        'strongest_month': strongest_month,
        'month_top_products': month_top_products,
        'month_top_services': month_top_services,
        'month_top_trainers': month_top_trainers,
    }

def redirect_back_to_reception(request):
    tab = request.POST.get('active_tab') or request.GET.get('tab')
    if tab in ['products', 'visits', 'schedule']:
        return redirect(f"{reverse('reception')}?{urlencode({'tab': tab})}")
    return redirect(request.META.get('HTTP_REFERER', 'reception'))


def redirect_back_to_finance(request):
    params = {}
    for key in ['report_date', 'report_month', 'report_year', 'archive_date', 'finance_type']:
        value = request.POST.get(key) or request.GET.get(key)
        if value:
            params[key] = value
    if params:
        return redirect(f"{reverse('finance')}?{urlencode(params)}")
    return redirect('finance')


def redirect_back_to_management(request):
    params = {}
    for key in ['q', 'user_role']:
        value = request.POST.get(key) or request.GET.get(key)
        if value:
            params[key] = value
    if params:
        return redirect(f"{reverse('management')}?{urlencode(params)}")
    return redirect('management')


def home(request):
    if request.user.is_authenticated:
        if request.user.role == 'accounting':
            return redirect('finance')
        if request.user.role == 'employee':
            return redirect('reception')
        if request.user.role == 'admin':
            return redirect('management')

    public_price_names = ['Игра за 1 час', 'Наем на ракета', 'Наем на перо']
    products = Product.objects.filter(name__in=public_price_names, is_active=True)
    products = sorted(products, key=lambda product: public_price_names.index(product.name))
    trainers = TrainerProfile.objects.all()
    context = {'products': products, 'trainers': trainers}
    return render(request, 'home.html', context)

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Акаунтът {username} е създаден успешно! Вече можете да влезете.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

def schedule(request):
    if request.user.is_authenticated and request.user.role == 'accounting':
        return redirect('finance')

    selected_date, min_booking_date, max_booking_date, date_was_clamped = parse_schedule_date(request.GET.get('date'), request.user)
    if date_was_clamped:
        messages.warning(request, 'Можете да запазвате часове само в позволения период за този профил.')

    courts = Court.objects.filter(is_active=True)
    start_hour = 8
    end_hour = 22
    hours_range = range(start_hour, end_hour)

    day_start, day_end = get_booking_day_bounds(selected_date)
    bookings = Booking.objects.filter(
        start_time__gte=day_start,
        start_time__lt=day_end,
        is_active=True,
    ).select_related('customer', 'trainer', 'court')
    trainer_options_by_hour = build_trainer_options_by_hour(selected_date)

    schedule_data = []
    for hour in hours_range:
        row = {'hour': f"{hour}:00"}
        slots = []
        for court in courts:
            is_taken = False
            booking_info = None
            for b in bookings:
                booking_local_start = get_booking_local_start(b)
                if b.court == court and booking_local_start.hour == hour and booking_local_start.date() == selected_date:
                    is_taken = True
                    booking_info = b
                    break
            slots.append({
                'court': court,
                'is_taken': is_taken,
                'is_bookable': is_slot_bookable(selected_date, hour),
                'booking': booking_info,
                'hour': hour
            })
        row['slots'] = slots
        schedule_data.append(row)

    context = {
        'schedule_data': schedule_data,
        'selected_date': selected_date,
        'courts': courts,
        'next_day': str(selected_date + timedelta(days=1)),
        'prev_day': str(selected_date - timedelta(days=1)),
        'today_date': str(min_booking_date),
        'min_booking_date': min_booking_date,
        'max_booking_date': max_booking_date,
        'can_go_prev_day': selected_date > min_booking_date,
        'can_go_next_day': selected_date < max_booking_date,
        'can_direct_booking': (not request.user.is_authenticated) or user_can_create_own_bookings(request.user),
        'show_booking_access_notice': request.user.is_authenticated and not user_can_create_own_bookings(request.user),
        'can_view_customer_names': (
            request.user.is_authenticated
            and request.user.role in ['admin', 'employee']
        ),
        'schedule_trainer_options_json': json.dumps(
            {str(hour): options for hour, options in trainer_options_by_hour.items()},
            ensure_ascii=False,
        ),
    }
    return render(request, 'schedule.html', context)

def make_booking(request):
    if not request.user.is_authenticated:
        messages.warning(
            request,
            'Моля, влезте първо в акаунта си, за да запазите час!'
        )
        return redirect(f"{reverse('login')}?next={reverse('schedule')}")

    if request.method == 'POST':
        date_str = request.POST.get('date')
        hour = int(request.POST.get('hour'))
        court_id = int(request.POST.get('court_id'))
        trainer_id = request.POST.get('trainer_id') or ''
        training_type = (request.POST.get('training_type') or '').strip()
        
        court = Court.objects.get(id=court_id)
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = get_slot_start(date_obj, hour)
        end_time = start_time + timedelta(hours=1)

        customer = request.user
        customer_id = request.POST.get('customer_id')
        if customer_id:
            if request.user.is_superuser or request.user.role in ['admin', 'employee']:
                customer = get_object_or_404(User, id=customer_id)
            else:
                messages.error(request, 'Нямате права да запазвате час за друг клиент.')
                return redirect(request.META.get('HTTP_REFERER', 'schedule'))

        elif not user_can_create_own_bookings(request.user):
            messages.error(request, 'Този профил няма достъп до директни резервации на кортове.')
            return redirect(request.META.get('HTTP_REFERER', 'schedule'))

        if not is_date_in_booking_window(date_obj, customer):
            messages.error(request, 'Можете да запазвате часове само в позволения период за този профил.')
            return redirect(request.META.get('HTTP_REFERER', 'schedule'))

        if not is_slot_bookable(date_obj, hour):
            messages.error(request, 'Този час вече е изминал и не може да бъде запазен.')
            return redirect(request.META.get('HTTP_REFERER', 'schedule'))

        trainer = None
        slot_trainer_options = build_trainer_options_by_hour(date_obj).get(hour, [])
        slot_trainer_options_by_id = {
            option['id']: option
            for option in slot_trainer_options
        }

        if trainer_id or training_type:
            if not trainer_id or not training_type:
                messages.error(request, 'За резервация с треньор трябва да изберете и треньор, и вид тренировка.')
                return redirect(request.META.get('HTTP_REFERER', 'schedule'))

            try:
                trainer_id = int(trainer_id)
            except ValueError:
                messages.error(request, 'Невалиден избор на треньор.')
                return redirect(request.META.get('HTTP_REFERER', 'schedule'))

            trainer_option = slot_trainer_options_by_id.get(trainer_id)
            if not trainer_option:
                messages.error(request, 'За този ден и час няма наличен избраният треньор.')
                return redirect(request.META.get('HTTP_REFERER', 'schedule'))

            if training_type not in trainer_option['training_type_values']:
                messages.error(request, 'Избраният вид тренировка не е наличен за този треньор в този час.')
                return redirect(request.META.get('HTTP_REFERER', 'schedule'))

            trainer = get_object_or_404(User, id=trainer_id, role='trainer')
            trainer_is_busy = Booking.objects.filter(
                trainer=trainer,
                start_time=start_time,
                is_active=True,
            ).exists()
            if trainer_is_busy:
                messages.error(request, f'Треньор {trainer.get_full_name() or trainer.username} вече има записана тренировка за този час.')
                return redirect(request.META.get('HTTP_REFERER', 'schedule'))

        exists = Booking.objects.filter(court=court, start_time=start_time, is_active=True).exists()

        if customer.role == 'customer':
            customer_day_start, customer_day_end = get_booking_day_bounds(date_obj)
            customer_daily_bookings = Booking.objects.filter(
                customer=customer,
                start_time__gte=customer_day_start,
                start_time__lt=customer_day_end,
                is_active=True,
            ).count()
            if customer_daily_bookings >= MAX_DAILY_BOOKINGS_PER_CUSTOMER:
                messages.error(
                    request,
                    f'Клиент може да има най-много {MAX_DAILY_BOOKINGS_PER_CUSTOMER} активни резервации за един ден.',
                )
                return redirect(request.META.get('HTTP_REFERER', 'schedule'))
        
        if exists:
            messages.error(request, 'Грешка: Този час вече е зает!')
        else:
            booking = Booking.objects.create(
                court=court,
                customer=customer,
                trainer=trainer,
                start_time=start_time,
                end_time=end_time,
                payment_status='not_paid',
                training_type=training_type,
            )
            success_message = f'Успешно запазихте час за {customer.get_full_name() or customer.username}!'
            if booking.trainer and booking.training_type:
                success_message += (
                    f" Тренировка с {booking.trainer.get_full_name() or booking.trainer.username} "
                    f"({booking.get_training_type_display()})."
                )
            messages.success(request, success_message)
            
        return redirect(request.META.get('HTTP_REFERER', 'schedule'))
    return redirect('schedule')


def booking_login_required(request):
    messages.warning(
        request,
        'Моля, влезте първо в акаунта си, за да запазите час!'
    )
    next_url = request.GET.get('next') or reverse('schedule')
    return redirect(f"{reverse('login')}?next={quote(next_url, safe='/')}")

@login_required
def profile(request):
    if request.user.role == 'accounting':
        return redirect('finance')

    if request.user.role == 'customer':
        Booking.objects.filter(
            customer=request.user,
            is_active=False,
            cancellation_reason__gt='',
            cancellation_seen_by_customer=False,
        ).update(cancellation_seen_by_customer=True)

    customer_edit_form = None
    photo_form = None

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            if request.user.role not in ['customer', 'trainer']:
                messages.error(request, 'Само клиентски и треньорски профили могат да редактират тези данни.')
                return redirect('profile')

            customer_edit_form = CustomerProfileEditForm(request.POST, instance=request.user)
            photo_form = ProfilePhotoForm(instance=request.user)
            if customer_edit_form.is_valid():
                customer_edit_form.save()
                messages.success(request, 'Профилът беше обновен успешно.')
                return redirect('profile')
            messages.error(request, 'Моля, коригирайте отбелязаните полета и опитайте отново.')

        elif action == 'update_photo':
            photo_form = ProfilePhotoForm(request.POST, request.FILES, instance=request.user)
            if request.user.role in ['customer', 'trainer']:
                customer_edit_form = CustomerProfileEditForm(instance=request.user)
            if photo_form.is_valid():
                photo_form.save()
                messages.success(request, 'Профилната снимка беше обновена успешно.')
                return redirect('profile')
            messages.error(request, 'Не успяхме да обновим снимката. Проверете избраните данни.')

    is_trainer_profile = request.user.role == 'trainer'
    is_accounting_profile = request.user.role == 'accounting'
    if is_trainer_profile:
        bookings = (
            Booking.objects
            .filter(trainer=request.user)
            .select_related('court', 'customer', 'trainer')
            .order_by('-start_time')
        )
    elif is_accounting_profile:
        bookings = Booking.objects.none()
    else:
        bookings = (
            Booking.objects
            .filter(customer=request.user)
            .select_related('court', 'customer', 'trainer')
            .order_by('-start_time')
        )

    if customer_edit_form is None and request.user.role in ['customer', 'trainer']:
        customer_edit_form = CustomerProfileEditForm(instance=request.user)
    if photo_form is None:
        photo_form = ProfilePhotoForm(instance=request.user)

    context = {
        'bookings': bookings,
        'now': timezone.now(),
        'is_trainer_profile': is_trainer_profile,
        'is_accounting_profile': is_accounting_profile,
        'customer_edit_form': customer_edit_form,
        'photo_form': photo_form,
    }
    return render(request, 'profile.html', context)


@login_required
def management(request):
    if not user_can_access_management(request.user):
        return redirect('home')

    search_query = (request.GET.get('q') or '').strip()
    user_role_filter = (request.GET.get('user_role') or '').strip()

    users = User.objects.order_by('role', 'username')
    if user_role_filter:
        users = users.filter(role=user_role_filter)
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone__icontains=search_query)
        )

    products = Product.objects.filter(category__in=['drink', 'product']).order_by('is_active', 'category', 'name')
    services = Product.objects.filter(category__in=RECEPTION_SERVICE_CATEGORIES).order_by('is_active', 'category', 'name')
    if search_query:
        product_search = Q(name__icontains=search_query) | Q(description__icontains=search_query)
        products = products.filter(product_search)
        services = services.filter(product_search)

    edited_user_id = None
    edited_product_id = None
    edited_service_id = None
    bound_user_form = None
    bound_product_form = None
    bound_service_form = None
    new_product_form = AdminCatalogItemForm(prefix='new_product', allowed_categories=['drink', 'product'])
    new_service_form = AdminCatalogItemForm(prefix='new_service', allowed_categories=RECEPTION_SERVICE_CATEGORIES)

    def add_form_errors(form):
        for field_errors in form.errors.values():
            for error_text in field_errors:
                messages.error(request, error_text)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_user':
            edited_user_id = int(request.POST.get('user_id') or 0)
            target_user = get_object_or_404(User, id=edited_user_id)
            bound_user_form = AdminUserManagementForm(request.POST, instance=target_user, prefix=f'user_{target_user.id}')
            if bound_user_form.is_valid():
                updated_user = bound_user_form.save(commit=False)
                if target_user == request.user and (not updated_user.is_active or updated_user.role != 'admin'):
                    messages.error(request, 'Не можете да деактивирате собствения си администраторски профил или да му смените ролята.')
                else:
                    updated_user.save()
                    messages.success(request, f'Потребителят {updated_user.username} беше обновен успешно.')
                    return redirect_back_to_management(request)
            else:
                add_form_errors(bound_user_form)

        elif action == 'update_product':
            edited_product_id = int(request.POST.get('product_id') or 0)
            target_product = get_object_or_404(Product, id=edited_product_id, category__in=['drink', 'product'])
            bound_product_form = AdminCatalogItemForm(
                request.POST,
                instance=target_product,
                prefix=f'product_{target_product.id}',
                allowed_categories=['drink', 'product'],
            )
            if bound_product_form.is_valid():
                bound_product_form.save()
                messages.success(request, f'Продуктът {target_product.name} беше обновен успешно.')
                return redirect_back_to_management(request)
            add_form_errors(bound_product_form)

        elif action == 'update_service':
            edited_service_id = int(request.POST.get('service_id') or 0)
            target_service = get_object_or_404(Product, id=edited_service_id, category__in=RECEPTION_SERVICE_CATEGORIES)
            bound_service_form = AdminCatalogItemForm(
                request.POST,
                instance=target_service,
                prefix=f'service_{target_service.id}',
                allowed_categories=RECEPTION_SERVICE_CATEGORIES,
            )
            if bound_service_form.is_valid():
                bound_service_form.save()
                messages.success(request, f'Услугата {target_service.name} беше обновена успешно.')
                return redirect_back_to_management(request)
            add_form_errors(bound_service_form)

        elif action == 'add_product':
            new_product_form = AdminCatalogItemForm(
                request.POST,
                prefix='new_product',
                allowed_categories=['drink', 'product'],
            )
            if new_product_form.is_valid():
                created_product = new_product_form.save()
                messages.success(request, f'Продуктът {created_product.name} беше добавен успешно.')
                return redirect_back_to_management(request)
            add_form_errors(new_product_form)

        elif action == 'add_service':
            new_service_form = AdminCatalogItemForm(
                request.POST,
                prefix='new_service',
                allowed_categories=RECEPTION_SERVICE_CATEGORIES,
            )
            if new_service_form.is_valid():
                created_service = new_service_form.save()
                messages.success(request, f'Услугата {created_service.name} беше добавена успешно.')
                return redirect_back_to_management(request)
            add_form_errors(new_service_form)

        elif action == 'toggle_product_active':
            target_product = get_object_or_404(Product, id=int(request.POST.get('product_id') or 0), category__in=['drink', 'product'])
            target_product.is_active = not target_product.is_active
            target_product.save(update_fields=['is_active'])
            messages.success(
                request,
                f"Продуктът {target_product.name} беше {'възстановен' if target_product.is_active else 'архивиран'} успешно.",
            )
            return redirect_back_to_management(request)

        elif action == 'toggle_service_active':
            target_service = get_object_or_404(Product, id=int(request.POST.get('service_id') or 0), category__in=RECEPTION_SERVICE_CATEGORIES)
            target_service.is_active = not target_service.is_active
            target_service.save(update_fields=['is_active'])
            messages.success(
                request,
                f"Услугата {target_service.name} беше {'възстановена' if target_service.is_active else 'архивирана'} успешно.",
            )
            return redirect_back_to_management(request)

    managed_users = [
        {
            'user': managed_user,
            'form': bound_user_form if edited_user_id == managed_user.id and bound_user_form else AdminUserManagementForm(
                instance=managed_user,
                prefix=f'user_{managed_user.id}',
            ),
        }
        for managed_user in users
    ]
    managed_products = [
        {
            'product': product,
            'form': bound_product_form if edited_product_id == product.id and bound_product_form else AdminCatalogItemForm(
                instance=product,
                prefix=f'product_{product.id}',
                allowed_categories=['drink', 'product'],
            ),
        }
        for product in products
    ]
    managed_services = [
        {
            'service': service,
            'form': bound_service_form if edited_service_id == service.id and bound_service_form else AdminCatalogItemForm(
                instance=service,
                prefix=f'service_{service.id}',
                allowed_categories=RECEPTION_SERVICE_CATEGORIES,
            ),
        }
        for service in services
    ]

    context = {
        'managed_users': managed_users,
        'managed_products': managed_products,
        'managed_services': managed_services,
        'new_product_form': new_product_form,
        'new_service_form': new_service_form,
        'active_users_count': users.filter(is_active=True).count(),
        'low_stock_products_count': Product.objects.filter(is_active=True, category__in=['drink', 'product'], quantity__isnull=False, quantity__lte=5).count(),
        'search_query': search_query,
        'user_role_filter': user_role_filter,
        'role_filter_choices': User.ROLE_CHOICES,
    }
    return render(request, 'management.html', context)


@login_required
def finance(request):
    if not user_can_access_finance(request.user):
        return redirect('home')

    reports_context = build_reception_reports_context(request)
    expense_form = ExpenseForm()

    context = {
        **reports_context,
        'products': Product.objects.filter(is_active=True).exclude(category__in=RECEPTION_SERVICE_CATEGORIES).order_by('category', 'name'),
        'services': Product.objects.filter(is_active=True, category__in=RECEPTION_SERVICE_CATEGORIES).order_by('category', 'name'),
        'sales_history': (
            Sale.objects
            .select_related('cashier')
            .prefetch_related('saleitem_set__product')
            .order_by('-created_at')[:15]
        ),
        'cash_movements': reports_context['cash_transactions'],
        'expense_form': expense_form,
    }
    return render(request, 'finance.html', context)


@login_required
def add_expense(request):
    if not user_can_access_finance(request.user):
        return redirect('home')

    if request.method != 'POST':
        return redirect_back_to_finance(request)

    form = ExpenseForm(request.POST)
    if not form.is_valid():
        for error in form.errors.values():
            for message_text in error:
                messages.error(request, message_text)
        return redirect_back_to_finance(request)

    expense = form.save(commit=False)
    expense.created_by = request.user

    today_start, _, _ = get_report_periods()
    shift_start = get_current_shift_start(today_start)
    current_cash_balance = money_sum(
        CashTransaction.objects.filter(created_at__gte=shift_start),
        'amount',
    )

    if expense.payment_method == 'cash' and expense.amount > current_cash_balance:
        messages.error(
            request,
            f'Не може да извадите {expense.amount:.2f} евро, защото в касата има само {current_cash_balance:.2f} евро.',
        )
        return redirect_back_to_finance(request)

    with transaction.atomic():
        expense.save()
        if expense.payment_method == 'cash':
            CashTransaction.objects.create(
                cashier=request.user,
                transaction_type='out',
                amount=-expense.amount,
                comment=f'Разход: {expense.title}',
            )

    messages.success(request, 'Разходът е добавен успешно.')
    return redirect_back_to_finance(request)

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    
    if booking.customer == request.user or request.user.role in ['admin', 'employee'] or request.user.is_superuser:
        if booking.start_time > timezone.now():
            booking.delete()
            messages.success(request, 'Резервацията беше отказана успешно.')
        else:
            messages.error(request, 'Не можете да отказвате минали резервации!')
    else:
        messages.error(request, 'Нямате права да изтриете тази резервация.')
        
    return redirect(request.META.get('HTTP_REFERER', 'profile'))


@login_required
def trainer_cancel_booking(request, booking_id):
    if request.method != 'POST':
        return redirect('profile')

    booking = get_object_or_404(
        Booking.objects.select_related('trainer', 'customer', 'court'),
        id=booking_id,
    )

    if request.user.role != 'trainer' or booking.trainer != request.user:
        messages.error(request, 'Нямате право да отменяте тази тренировка.')
        return redirect('profile')

    if not booking.is_active:
        messages.warning(request, 'Тази тренировка вече е отменена.')
        return redirect('profile')

    if booking.start_time <= timezone.now():
        messages.error(request, 'Не може да отменяте тренировки, които вече са започнали или са минали.')
        return redirect('profile')

    cancellation_reason = (request.POST.get('cancellation_reason') or '').strip()
    if not cancellation_reason:
        messages.error(request, 'Моля, добавете причина за отмяна, за да бъде информиран клиентът.')
        return redirect('profile')

    booking.is_active = False
    booking.cancellation_reason = cancellation_reason
    booking.cancelled_at = timezone.now()
    booking.cancellation_seen_by_customer = False
    booking.cancelled_by = request.user
    booking.save(update_fields=['is_active', 'cancellation_reason', 'cancelled_at', 'cancellation_seen_by_customer', 'cancelled_by'])

    customer_name = booking.customer.get_full_name() or booking.customer.username
    messages.success(request, f'Тренировката на {customer_name} беше отменена успешно.')
    return redirect('profile')


@login_required
def staff_cancel_booking(request, booking_id):
    if request.method != 'POST':
        return redirect('reception')

    if not (request.user.is_superuser or request.user.role in ['admin', 'employee']):
        return redirect('home')

    booking = get_object_or_404(
        Booking.objects.select_related('trainer', 'customer', 'court'),
        id=booking_id,
    )

    if not booking.is_active:
        messages.warning(request, 'Тази резервация вече е отменена.')
        return redirect_back_to_reception(request)

    if booking.start_time <= timezone.now():
        messages.error(request, 'Не може да отменяте резервации, които вече са започнали или са минали.')
        return redirect_back_to_reception(request)

    cancellation_reason = (request.POST.get('cancellation_reason') or '').strip()
    if not cancellation_reason:
        messages.error(request, 'Моля, добавете причина за отмяна, за да бъде информиран клиентът.')
        return redirect_back_to_reception(request)

    booking.is_active = False
    booking.cancellation_reason = cancellation_reason
    booking.cancelled_at = timezone.now()
    booking.cancellation_seen_by_customer = False
    booking.cancelled_by = request.user
    booking.save(update_fields=['is_active', 'cancellation_reason', 'cancelled_at', 'cancellation_seen_by_customer', 'cancelled_by'])

    customer_name = booking.customer.get_full_name() or booking.customer.username
    messages.success(request, f'Резервацията на {customer_name} беше отменена успешно.')
    return redirect_back_to_reception(request)

@login_required
def reception(request):
    if not user_can_access_reception(request.user):
        return redirect('home')

    selected_date, min_booking_date, max_booking_date, date_was_clamped = parse_schedule_date(request.GET.get('date'), request.user)
    if date_was_clamped:
        messages.warning(request, 'Можете да запазвате часове само в позволения период за този профил.')

    all_products = Product.objects.filter(is_active=True)
    products = all_products.filter(category__in=['drink', 'product']).order_by('category', 'name')
    service_products = all_products.filter(category__in=RECEPTION_SERVICE_CATEGORIES).order_by('category', 'name')
    bill = get_reception_bill(request)
    bill_context = build_reception_bill_context(bill)
    reports_context = build_reception_reports_context(request)
    courts = Court.objects.filter(is_active=True)
    hours_range = range(8, 22)
    
    day_start, day_end = get_booking_day_bounds(selected_date)
    daily_bookings = Booking.objects.filter(
        start_time__gte=day_start,
        start_time__lt=day_end,
        is_active=True,
    ).select_related('customer', 'trainer', 'court').order_by('start_time')
    trainer_options_by_hour = build_trainer_options_by_hour(selected_date)

    schedule_data = []
    for hour in hours_range:
        row = {'hour': f"{hour}:00"}
        slots = []
        for court in courts:
            booking_info = None
            for booking in daily_bookings:
                booking_local_start = get_booking_local_start(booking)
                if booking.court == court and booking_local_start.hour == hour and booking_local_start.date() == selected_date:
                    booking_info = booking
                    break
            slots.append({
                'court': court,
                'hour': hour,
                'is_taken': booking_info is not None,
                'is_bookable': is_slot_bookable(selected_date, hour),
                'booking': booking_info,
            })
        row['slots'] = slots
        schedule_data.append(row)

    search_query = request.GET.get('q')
    found_users = None
    if search_query:
        found_users = User.objects.annotate(
            full_name=Concat('first_name', Value(' '), 'last_name')
        ).filter(
            is_active=True
        ).filter(
            Q(username__icontains=search_query) | 
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    context = {
        'selected_date': selected_date,
        'products': products,
        'service_products': service_products,
        'bookings': daily_bookings,
        'schedule_data': schedule_data,
        'found_users': found_users,
        'search_query': search_query,
        'courts': courts,
        'hours_range': hours_range,
        'next_day': str(selected_date + timedelta(days=1)),
        'prev_day': str(selected_date - timedelta(days=1)),
        'today_date': str(min_booking_date),
        'min_booking_date': min_booking_date,
        'max_booking_date': max_booking_date,
        'can_go_prev_day': selected_date > min_booking_date,
        'can_go_next_day': selected_date < max_booking_date,
        'bill_items': bill_context['items'],
        'bill_total': bill_context['total'],
        'bill_count': bill_context['count'],
        'schedule_trainer_options_json': json.dumps(
            {str(hour): options for hour, options in trainer_options_by_hour.items()},
            ensure_ascii=False,
        ),
        **reports_context,
    }
    return render(request, 'reception.html', context)

@login_required
def add_to_bill(request, product_id):
    if not user_can_access_reception(request.user):
        return redirect('home')

    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id, is_active=True)
        bill = get_reception_bill(request)
        product_key = str(product.id)
        current_quantity = int(bill.get(product_key, 0))

        if product.quantity is not None and current_quantity >= product.quantity:
            messages.error(request, 'Няма достатъчна наличност за този продукт!')
        else:
            bill[product_key] = current_quantity + 1
            save_reception_bill(request, bill)
            messages.success(request, f'Добавено в сметката: {product.name}.')

    return redirect_back_to_reception(request)


@login_required
def decrease_bill_item(request, product_id):
    if not user_can_access_reception(request.user):
        return redirect('home')

    if request.method == 'POST':
        bill = get_reception_bill(request)
        product_key = str(product_id)
        if product_key in bill:
            if bill[product_key] > 1:
                bill[product_key] -= 1
            else:
                bill.pop(product_key)
            save_reception_bill(request, bill)

    return redirect_back_to_reception(request)


@login_required
def remove_bill_item(request, product_id):
    if not user_can_access_reception(request.user):
        return redirect('home')

    if request.method == 'POST':
        bill = get_reception_bill(request)
        bill.pop(str(product_id), None)
        save_reception_bill(request, bill)

    return redirect_back_to_reception(request)


@login_required
def clear_bill(request):
    if not user_can_access_reception(request.user):
        return redirect('home')

    if request.method == 'POST':
        request.session.pop(RECEPTION_BILL_SESSION_KEY, None)
        request.session.modified = True
        messages.success(request, 'Сметката е изчистена.')

    return redirect_back_to_reception(request)


@login_required
def checkout_bill(request):
    if not user_can_access_reception(request.user):
        return redirect('home')

    bill = get_reception_bill(request)
    if request.method != 'POST' or not bill:
        messages.warning(request, 'Сметката е празна.')
        return redirect_back_to_reception(request)

    payment_method = request.POST.get('payment_method', 'cash')
    if payment_method not in ['cash', 'card']:
        payment_method = 'cash'

    with transaction.atomic():
        product_ids = [int(product_id) for product_id in bill.keys()]
        products_by_id = Product.objects.select_for_update().in_bulk(product_ids)
        total = Decimal('0.00')

        for product_id, quantity in bill.items():
            product = products_by_id.get(int(product_id))
            if not product:
                messages.error(request, 'В сметката има продукт, който вече не съществува.')
                return redirect_back_to_reception(request)
            if product.quantity is not None and product.quantity < quantity:
                messages.error(request, f'Няма достатъчна наличност за {product.name}.')
                return redirect_back_to_reception(request)

        sale = Sale.objects.create(
            cashier=request.user,
            total_amount=Decimal('0.00'),
            payment_method=payment_method,
        )

        for product_id, quantity in bill.items():
            product = products_by_id[int(product_id)]
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                price_at_sale=product.price,
            )
            total += product.price * quantity

            if product.quantity is not None:
                product.quantity -= quantity
                product.save(update_fields=['quantity'])

        sale.total_amount = total
        sale.save(update_fields=['total_amount'])

        if payment_method == 'cash' and total:
            CashTransaction.objects.create(
                cashier=request.user,
                sale=sale,
                transaction_type='sale',
                amount=total,
                comment=f'Продажба #{sale.id}',
            )

    request.session.pop(RECEPTION_BILL_SESSION_KEY, None)
    request.session.modified = True
    payment_label = 'в брой' if payment_method == 'cash' else 'с карта'
    messages.success(request, f'Сметката е приключена {payment_label}. Общо: {total:.2f} €.')
    return redirect_back_to_reception(request)


@login_required
def add_cash_transaction(request):
    if not user_can_access_reception(request.user):
        return redirect('home')

    if request.method == 'POST':
        transaction_type = request.POST.get('transaction_type')
        comment = request.POST.get('comment', '').strip()

        try:
            amount = Decimal(request.POST.get('amount', '0'))
        except Exception:
            amount = Decimal('0')

        if amount <= 0:
            messages.error(request, 'Въведете сума по-голяма от 0.')
            return redirect_back_to_reception(request)

        if transaction_type == 'out':
            today_start, _, _ = get_report_periods()
            shift_start = get_current_shift_start(today_start)
            current_cash_balance = money_sum(
                CashTransaction.objects.filter(created_at__gte=shift_start),
                'amount',
            )
            if amount > current_cash_balance:
                messages.error(
                    request,
                    f'Не може да извадите {amount:.2f} €, защото в касата има само {current_cash_balance:.2f} €.',
                )
                return redirect_back_to_reception(request)
            amount = -amount
        elif transaction_type != 'in':
            messages.error(request, 'Невалиден тип касова операция.')
            return redirect_back_to_reception(request)

        CashTransaction.objects.create(
            cashier=request.user,
            transaction_type=transaction_type,
            amount=amount,
            comment=comment,
        )
        messages.success(request, 'Касовата операция е записана.')

    return redirect_back_to_reception(request)


@login_required
def close_day(request):
    if not user_can_access_reception(request.user):
        return redirect('home')

    if request.method != 'POST':
        return redirect('reception')

    bill = get_reception_bill(request)
    if bill:
        messages.error(request, 'Не може да приключите деня, докато има активна сметка.')
        return redirect_back_to_reception(request)

    today_start, _, _ = get_report_periods()
    shift_start = get_current_shift_start(today_start)
    report_snapshot = build_shift_report_snapshot(shift_start)
    sales_total = Decimal(report_snapshot['totals']['sales_total'])
    cash_total = Decimal(report_snapshot['totals']['cash_total'])
    card_total = Decimal(report_snapshot['totals']['card_total'])
    cash_balance = Decimal(report_snapshot['totals']['cash_balance'])
    attendance = report_snapshot['attendance']
    comment = request.POST.get('comment', '').strip() or 'Приключване на деня'

    with transaction.atomic():
        if cash_balance:
            CashTransaction.objects.create(
                cashier=request.user,
                transaction_type='out' if cash_balance > 0 else 'in',
                amount=-cash_balance,
                comment=comment,
            )

        ShiftClose.objects.create(
            cashier=request.user,
            shift_started_at=shift_start,
            sales_total=sales_total,
            cash_total=cash_total,
            card_total=card_total,
            cash_balance=cash_balance,
            sales_count=report_snapshot['sales_count'],
            cash_transactions_count=report_snapshot['cash_transactions_count'],
            attendance=attendance,
            report_data=report_snapshot,
            comment=comment,
        )

    messages.success(request, 'Денят е приключен. Текущите дневни данни са нулирани.')
    return redirect('reception')


@login_required
def void_sale(request, sale_id):
    if not user_can_access_reception(request.user):
        return redirect('home')

    if request.method != 'POST':
        return redirect('reception')

    today_start, _, _ = get_report_periods()
    shift_start = get_current_shift_start(today_start)
    sale = get_object_or_404(Sale.objects.prefetch_related('saleitem_set__product'), id=sale_id)
    report_date = request.POST.get('report_date') or timezone.localtime().date().isoformat()

    if sale.created_at < shift_start:
        messages.error(request, 'Може да сторнирате само продажби от текущата смяна.')
        return redirect(f"{reverse('reception')}?{urlencode({'report_date': report_date, 'open_report': 'daily'})}")

    with transaction.atomic():
        sale_items = list(sale.saleitem_set.select_related('product'))
        for item in sale_items:
            if item.product and item.product.quantity is not None:
                item.product.quantity += item.quantity
                item.product.save(update_fields=['quantity'])

        if sale.payment_method == 'cash':
            CashTransaction.objects.create(
                cashier=request.user,
                transaction_type='out',
                amount=-sale.total_amount,
                comment=f'Сторно продажба #{sale.id}',
            )
        sale.delete()

    if sale.payment_method == 'cash':
        messages.success(request, 'Продажбата е сторнирана успешно и сумата е извадена от касата.')
    else:
        messages.success(request, 'Картовата продажба е сторнирана успешно. Касата не е променена.')
    return redirect(f"{reverse('reception')}?{urlencode({'report_date': report_date, 'open_report': 'daily'})}")


@login_required
def reception_exit(request):
    if not user_can_access_reception(request.user):
        return redirect('home')

    if get_reception_bill(request):
        messages.error(request, 'Има активна сметка. Приключете или изчистете текущата продажба преди изход.')
        return redirect('reception')

    today_start, _, _ = get_report_periods()
    if has_reception_activity_since_last_close(today_start):
        messages.error(request, 'Трябва първо да приключите деня, преди да излезете от рецепцията.')
        return redirect('reception')

    auth_logout(request)
    return redirect('home')

@login_required
def mark_paid(request, booking_id):
    if not (request.user.is_superuser or request.user.role in ['admin', 'employee']):
        return redirect('home')
        
    booking = get_object_or_404(Booking, id=booking_id)
    booking.payment_status = 'cash' # Засега по подразбиране е Кеш
    booking.save()
    
    messages.success(request, f'Резервацията на {booking.customer} беше маркирана като платена.')
    return redirect(request.META.get('HTTP_REFERER', 'reception'))

