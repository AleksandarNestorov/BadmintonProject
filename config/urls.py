from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from bookings import views  # <-- Увери се, че импортираш views от приложението bookings

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- ОСНОВНИ СТРАНИЦИ ---
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),

    # --- ВХОД И ИЗХОД ---
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='logout.html'), name='logout'),

    # --- ГРАФИК И РЕЗЕРВАЦИИ ---
    path('schedule/', views.schedule, name='schedule'),
    path('booking/login-required/', views.booking_login_required, name='booking_login_required'),
    path('booking/make/', views.make_booking, name='make_booking'),
    path('booking/cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('booking/pay/<int:booking_id>/', views.mark_paid, name='mark_paid'),

    # --- РЕЦЕПЦИЯ (Това липсваше!) ---
    path('reception/', views.reception, name='reception'),
    path('reception/sell/<int:product_id>/', views.sell_product, name='sell_product'),
]
