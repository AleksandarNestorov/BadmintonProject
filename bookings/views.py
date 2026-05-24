from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Product, TrainerProfile, Court, Booking, Sale, SaleItem, CashTransaction, ShiftClose, User
from .forms import UserRegisterForm
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
BOOKING_TIME_ZONE = ZoneInfo('Europe/Sofia')
RECEPTION_BILL_SESSION_KEY = 'reception_bill'
RECEPTION_SERVICE_CATEGORIES = ['game', 'rental', 'stringing', 'training']


def get_slot_start(selected_date, hour):
    slot_start = datetime.combine(selected_date, time(hour, 0))
    return timezone.make_aware(slot_start, timezone.get_current_timezone())


def is_slot_bookable(selected_date, hour):
    local_slot_start = datetime.combine(
        selected_date,
        time(hour, 0),
        tzinfo=BOOKING_TIME_ZONE,
    )
    return datetime.now(BOOKING_TIME_ZONE) < local_slot_start + BOOKING_GRACE_PERIOD


def user_can_access_reception(user):
    return user.is_superuser or user.role in ['admin', 'employee']


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

    product_summary = {}
    service_summary = {}

    serialized_sales = []
    for sale in sales:
        serialized_items = []
        for item in sale.saleitem_set.all():
            product = item.product
            item_name = product.name if product else 'Изтрит продукт'
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
            'cash_balance': money_text(cash_balance),
        },
        'sales_count': len(sales),
        'cash_transactions_count': len(cash_transactions),
        'attendance': attendance_sum(shift_start, end),
        'sales': serialized_sales,
        'product_summary': serialize_summary(product_summary),
        'service_summary': serialize_summary(service_summary),
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


def build_reception_reports_context(request):
    today_start, current_month_start, current_year_start = get_report_periods()
    selected_day_value = request.GET.get('report_date') or today_start.strftime('%Y-%m-%d')
    selected_month_value = request.GET.get('report_month') or current_month_start.strftime('%Y-%m')
    selected_year_value = request.GET.get('report_year') or str(current_year_start.year)
    selected_archive_value = request.GET.get('archive_date') or ''

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
        month_start, month_end = current_month_start, get_month_bounds(current_month_start.year, current_month_start.month)[1]
        selected_month_value = current_month_start.strftime('%Y-%m')

    try:
        selected_year = int(selected_year_value)
        year_start, year_end = get_year_bounds(selected_year)
    except (TypeError, ValueError):
        year_start, year_end = current_year_start, get_year_bounds(current_year_start.year)[1]
        selected_year = current_year_start.year

    first_sale = Sale.objects.order_by('created_at').first()
    first_year = timezone.localtime(first_sale.created_at).year if first_sale else current_year_start.year
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
    daily_sales = list(daily_sales_queryset.prefetch_related('saleitem_set__product').order_by('-created_at'))
    current_shift_report = build_shift_report_snapshot(shift_start)

    archive_is_filtered = False
    selected_archive_label = 'последни 30 приключвания'
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

    return {
        'cash_balance': money_sum(current_cash_transactions, 'amount'),
        'current_sales_total': money_sum(current_shift_sales),
        'current_card_sales_total': money_sum(current_shift_sales.filter(payment_method='card')),
        'today_sales_total': money_sum(daily_sales_queryset),
        'today_cash_sales_total': money_sum(daily_sales_queryset.filter(payment_method='cash')),
        'today_card_sales_total': money_sum(daily_sales_queryset.filter(payment_method='card')),
        'today_sales_count': daily_sales_queryset.count(),
        'today_attendance': attendance_sum(daily_start, day_end),
        'daily_cash_balance': money_sum(daily_cash_transactions, 'amount'),
        'selected_day_value': selected_day_value,
        'selected_day_label': day_start.strftime('%d.%m.%Y'),
        'current_shift_start': shift_start,
        'month_sales_total': money_sum(month_sales),
        'month_sales_count': month_sales.count(),
        'month_attendance': attendance_sum(month_start, month_end),
        'selected_month_value': selected_month_value,
        'selected_month_label': month_start.strftime('%m.%Y'),
        'year_sales_total': money_sum(year_sales),
        'year_sales_count': year_sales.count(),
        'year_attendance': attendance_sum(year_start, year_end),
        'selected_year': selected_year,
        'report_years': report_years,
        'recent_sales': daily_sales[:5],
        'daily_sales': daily_sales,
        'daily_sales_has_more': len(daily_sales) > 5,
        'cash_transactions': current_cash_transactions.order_by('-created_at')[:20],
        'recent_shift_closes': ShiftClose.objects.filter(closed_at__gte=day_start, closed_at__lt=day_end).order_by('-closed_at'),
        'current_shift_report': current_shift_report,
        'shift_close_archive': shift_close_archive,
        'selected_archive_value': selected_archive_value,
        'selected_archive_label': selected_archive_label,
        'archive_is_filtered': archive_is_filtered,
    }


def redirect_back_to_reception(request):
    tab = request.POST.get('active_tab') or request.GET.get('tab')
    if tab in ['products', 'visits', 'schedule']:
        return redirect(f"{reverse('reception')}?{urlencode({'tab': tab})}")
    return redirect(request.META.get('HTTP_REFERER', 'reception'))


# --- 1. НАЧАЛНА СТРАНИЦА ---
def home(request):
    public_price_names = ['Игра за 1 час', 'Наем на ракета', 'Наем на перо']
    products = Product.objects.filter(name__in=public_price_names)
    products = sorted(products, key=lambda product: public_price_names.index(product.name))
    trainers = TrainerProfile.objects.all()
    context = {'products': products, 'trainers': trainers}
    return render(request, 'home.html', context)

# --- 2. РЕГИСТРАЦИЯ ---
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

# --- 3. ГРАФИК (За Клиенти) ---
def schedule(request):
    date_str = request.GET.get('date')
    if date_str:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        selected_date = timezone.now().date()

    courts = Court.objects.filter(is_active=True)
    start_hour = 8
    end_hour = 22
    hours_range = range(start_hour, end_hour)

    bookings = Booking.objects.filter(start_time__date=selected_date, is_active=True)

    schedule_data = []
    for hour in hours_range:
        row = {'hour': f"{hour}:00"}
        slots = []
        for court in courts:
            is_taken = False
            booking_info = None
            for b in bookings:
                if b.court == court and b.start_time.hour == hour:
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
        'can_view_customer_names': (
            request.user.is_authenticated
            and request.user.role in ['admin', 'employee']
        ),
    }
    return render(request, 'schedule.html', context)

# --- 4. ЗАПАЗВАНЕ НА ЧАС ---
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
        
        court = Court.objects.get(id=court_id)
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = get_slot_start(date_obj, hour)
        end_time = start_time + timedelta(hours=1)

        if not is_slot_bookable(date_obj, hour):
            messages.error(request, 'Този час вече е изминал и не може да бъде запазен.')
            return redirect(request.META.get('HTTP_REFERER', 'schedule'))
        
        customer = request.user
        customer_id = request.POST.get('customer_id')
        if customer_id:
            if request.user.is_superuser or request.user.role in ['admin', 'employee']:
                customer = get_object_or_404(User, id=customer_id)
            else:
                messages.error(request, 'Нямате права да запазвате час за друг клиент.')
                return redirect(request.META.get('HTTP_REFERER', 'schedule'))

        exists = Booking.objects.filter(court=court, start_time=start_time, is_active=True).exists()
        
        if exists:
            messages.error(request, 'Грешка: Този час вече е зает!')
        else:
            Booking.objects.create(
                court=court,
                customer=customer,
                start_time=start_time,
                end_time=end_time,
                payment_status='not_paid'
            )
            messages.success(request, f'Успешно запазихте час за {customer.get_full_name() or customer.username}!')
            
        # Връщаме се там, откъдето сме дошли (или в графика, или в рецепцията)
        return redirect(request.META.get('HTTP_REFERER', 'schedule'))
    return redirect('schedule')


def booking_login_required(request):
    messages.warning(
        request,
        'Моля, влезте първо в акаунта си, за да запазите час!'
    )
    next_url = request.GET.get('next') or reverse('schedule')
    return redirect(f"{reverse('login')}?next={quote(next_url, safe='/')}")

# --- 5. ПРОФИЛ ---
@login_required
def profile(request):
    bookings = Booking.objects.filter(customer=request.user).order_by('-start_time')
    context = {'bookings': bookings, 'now': timezone.now()}
    return render(request, 'profile.html', context)

# --- 6. ОТКАЗ НА РЕЗЕРВАЦИЯ ---
@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Проверка: Клиентът трие свой час ИЛИ служител трие чужд час
    if booking.customer == request.user or request.user.role in ['admin', 'employee'] or request.user.is_superuser:
        if booking.start_time > timezone.now():
            booking.delete()
            messages.success(request, 'Резервацията беше отказана успешно.')
        else:
            messages.error(request, 'Не можете да отказвате минали резервации!')
    else:
        messages.error(request, 'Нямате права да изтриете тази резервация.')
        
    return redirect(request.META.get('HTTP_REFERER', 'profile'))

# --- 7. РЕЦЕПЦИЯ (Главен панел за служители) ---
@login_required
def reception(request):
    if not user_can_access_reception(request.user):
        return redirect('home')

    date_str = request.GET.get('date')
    if date_str:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        selected_date = timezone.now().date()

    all_products = Product.objects.all()
    products = all_products.filter(category__in=['drink', 'product']).order_by('category', 'name')
    service_products = all_products.filter(category__in=RECEPTION_SERVICE_CATEGORIES).order_by('category', 'name')
    bill = get_reception_bill(request)
    bill_context = build_reception_bill_context(bill)
    reports_context = build_reception_reports_context(request)
    courts = Court.objects.filter(is_active=True)
    hours_range = range(8, 22)
    
    daily_bookings = Booking.objects.filter(
        start_time__date=selected_date, 
        is_active=True
    ).order_by('start_time')

    schedule_data = []
    for hour in hours_range:
        row = {'hour': f"{hour}:00"}
        slots = []
        for court in courts:
            booking_info = None
            for booking in daily_bookings:
                if booking.court == court and booking.start_time.hour == hour:
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
        'bill_items': bill_context['items'],
        'bill_total': bill_context['total'],
        'bill_count': bill_context['count'],
        **reports_context,
    }
    return render(request, 'reception.html', context)

# --- 8. СМЕТКА НА РЕЦЕПЦИЯТА ---
@login_required
def add_to_bill(request, product_id):
    if not user_can_access_reception(request.user):
        return redirect('home')

    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
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
        messages.error(request, 'Има активна сметка. Приключете или изчистете сметката преди изход.')
        return redirect('reception')

    today_start, _, _ = get_report_periods()
    last_close = ShiftClose.objects.filter(closed_at__gte=today_start).order_by('-closed_at').first()
    latest_sale = Sale.objects.filter(created_at__gte=today_start).order_by('-created_at').first()
    latest_cash_transaction = CashTransaction.objects.filter(created_at__gte=today_start).order_by('-created_at').first()

    has_activity_after_close = (
        not last_close
        or (latest_sale and latest_sale.created_at > last_close.closed_at)
        or (
            latest_cash_transaction
            and latest_cash_transaction.created_at > last_close.closed_at
        )
    )

    if has_activity_after_close:
        messages.error(request, 'Първо трябва да приключите деня, преди да излезете от рецепцията.')
        return redirect('reception')

    return redirect('home')

# --- 9. МАРКИРАНЕ НА ПЛАЩАНЕ (ТОВА ЛИПСВАШЕ!) ---
@login_required
def mark_paid(request, booking_id):
    if not (request.user.is_superuser or request.user.role in ['admin', 'employee']):
        return redirect('home')
        
    booking = get_object_or_404(Booking, id=booking_id)
    booking.payment_status = 'cash' # Засега по подразбиране е Кеш
    booking.save()
    
    messages.success(request, f'Резервацията на {booking.customer} беше маркирана като платена.')
    return redirect(request.META.get('HTTP_REFERER', 'reception'))
