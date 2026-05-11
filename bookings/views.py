from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Product, TrainerProfile, Court, Booking, Sale, SaleItem, User
from .forms import UserRegisterForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta, time
from django.db.models import Q

# --- 1. НАЧАЛНА СТРАНИЦА ---
def home(request):
    products = Product.objects.all()
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
@login_required
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
    }
    return render(request, 'schedule.html', context)

# --- 4. ЗАПАЗВАНЕ НА ЧАС ---
@login_required
def make_booking(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        hour = int(request.POST.get('hour'))
        court_id = int(request.POST.get('court_id'))
        
        court = Court.objects.get(id=court_id)
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.combine(date_obj, time(hour, 0))
        end_time = start_time + timedelta(hours=1)
        
        # Резервацията се прави от името на текущия потребител (дори да е рецепционист)
        # В бъдеще може да добавим поле "client_name" за рецепцията.
        exists = Booking.objects.filter(court=court, start_time=start_time, is_active=True).exists()
        
        if exists:
            messages.error(request, 'Грешка: Този час вече е зает!')
        else:
            Booking.objects.create(
                court=court,
                customer=request.user,
                start_time=start_time,
                end_time=end_time,
                payment_status='not_paid'
            )
            messages.success(request, 'Успешно запазихте час!')
            
        # Връщаме се там, откъдето сме дошли (или в графика, или в рецепцията)
        return redirect(request.META.get('HTTP_REFERER', 'schedule'))
    return redirect('schedule')

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
    
    daily_bookings = Booking.objects.filter(
        start_time__date=selected_date, 
        is_active=True
    ).order_by('start_time')

    search_query = request.GET.get('q')
    found_users = None
    if search_query:
        found_users = User.objects.filter(
            Q(username__icontains=search_query) | 
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    context = {
        'selected_date': selected_date,
        'products': products,
        'bookings': daily_bookings,
        'found_users': found_users,
        'search_query': search_query,
        'courts': Court.objects.filter(is_active=True),
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