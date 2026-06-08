from .models import Booking


def profile_notifications(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or getattr(user, 'role', '') != 'customer':
        return {'profile_alert_count': 0}

    profile_alert_count = Booking.objects.filter(
        customer=user,
        is_active=False,
        cancellation_reason__gt='',
        cancellation_seen_by_customer=False,
    ).count()
    return {'profile_alert_count': profile_alert_count}
