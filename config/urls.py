from django.conf import settings
from django.conf.urls.static import static
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
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url='/password-reset/done/',
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url='/reset/done/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),

    # --- ГРАФИК И РЕЗЕРВАЦИИ ---
    path('schedule/', views.schedule, name='schedule'),
    path('booking/login-required/', views.booking_login_required, name='booking_login_required'),
    path('booking/make/', views.make_booking, name='make_booking'),
    path('booking/cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('booking/pay/<int:booking_id>/', views.mark_paid, name='mark_paid'),

    # --- РЕЦЕПЦИЯ (Това липсваше!) ---
    path('reception/', views.reception, name='reception'),
    path('reception/bill/add/<int:product_id>/', views.add_to_bill, name='add_to_bill'),
    path('reception/bill/decrease/<int:product_id>/', views.decrease_bill_item, name='decrease_bill_item'),
    path('reception/bill/remove/<int:product_id>/', views.remove_bill_item, name='remove_bill_item'),
    path('reception/bill/clear/', views.clear_bill, name='clear_bill'),
    path('reception/bill/checkout/', views.checkout_bill, name='checkout_bill'),
    path('reception/cash/add/', views.add_cash_transaction, name='add_cash_transaction'),
    path('reception/close-day/', views.close_day, name='close_day'),
    path('reception/sale/<int:sale_id>/void/', views.void_sale, name='void_sale'),
    path('reception/exit/', views.reception_exit, name='reception_exit'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
