from django.shortcuts import redirect


class AdminPanelAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            user = request.user
            can_access_admin = (
                user.is_authenticated
                and (
                    user.is_superuser
                    or getattr(user, 'role', None) == 'admin'
                )
            )

            if not can_access_admin:
                return redirect('home')

        return self.get_response(request)
