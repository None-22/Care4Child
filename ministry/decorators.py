from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse


def ministry_required(view_func):
    """
    Decorator that checks the user has the MINISTRY role (or is superuser).
    Redirects unauthorized users to the login page with an error message.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1. Check Authentication
        if not request.user.is_authenticated:
            return redirect('users:login')

        # 2. Check Role
        is_authorized = (
            request.user.is_superuser or
            getattr(request.user, 'role', None) == 'MINISTRY'
        )

        if is_authorized:
            return view_func(request, *args, **kwargs)

        # 3. Handle Unauthorized
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'غير مصرح لك بالوصول. هذه الصفحة مخصصة لوزارة الصحة.'}, status=403)

        messages.error(request, 'عذراً، هذه الصفحة مخصصة لمستخدمي وزارة الصحة فقط.')
        return redirect('users:login')

    return _wrapped_view
