from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Product, TrainerProfile, Court, Booking, Sale, SaleItem, User
from .forms import UserRegisterForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta, time
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.urls import reverse
from urllib.parse import quote
from zoneinfo import ZoneInfo

BOOKING_GRACE_PERIOD = timedelta(minutes=30)
BOOKING_TIME_ZONE = ZoneInfo('Europe/Sofia')


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


# --- 1. НАЧАЛНА СТРАНИЦА ---
def home(request):
    products = Product.objects.exclude(name__iexact='Минерална вода')
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
    if not (request.user.is_superuser or request.user.role in ['admin', 'employee']):
        return redirect('home')

    date_str = request.GET.get('date')
    if date_str:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        selected_date = timezone.now().date()

    products = Product.objects.all()
    service_products = products.filter(category__in=['service', 'equipment'])
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
    }
    return render(request, 'reception.html', context)

# --- 8. ПРОДАЖБА НА ПРОДУКТ (Бутончето 💰) ---
@login_required
def sell_product(request, product_id):
    if not (request.user.is_superuser or request.user.role in ['admin', 'employee']):
        return redirect('home')
        
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        if product.quantity > 0:
            product.quantity -= 1
            product.save()
            # Тук може да се добави запис в Sale/SaleItem, но за простота сега само намаляме бройката
            messages.success(request, f'Продадохте 1 бр. {product.name}.')
        else:
            messages.error(request, 'Няма наличност!')
    return redirect(request.META.get('HTTP_REFERER', 'reception'))

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
