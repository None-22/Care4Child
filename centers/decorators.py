from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse

def center_staff_required(view_func):
    """
    Decorator for views that checks that the user is a Center Staff, Manager, or Superuser.
    Allows access to all children (Unified Database) but restricts non-staff.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1. Check Authentication
        if not request.user.is_authenticated:
            return redirect('users:login')
            
        # 2. Check Role (Staff/Manager/Superuser)
        is_authorized = (
            request.user.is_superuser or 
            request.user.role in ['CENTER_STAFF', 'CENTER_MANAGER']
        )

        if is_authorized:
            return view_func(request, *args, **kwargs)
        
        # 3. Handle Unauthorized Access
        # Smart Handling: JSON for API/AJAX, Redirect for HTML
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
             return JsonResponse({'error': 'Permission Denied'}, status=403)
        
        messages.error(request, "عذراً، هذه الصفحة مخصصة لموظفي المراكز فقط.")
        return redirect('centers:dashboard')
        
    return _wrapped_view

def center_manager_required(view_func):
    """
    Decorator for views that checks that the user is a Center Manager or Superuser.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1. Check Authentication
        if not request.user.is_authenticated:
            return redirect('users:login')
            
        # 2. Check Role (Manager/Superuser)
        is_authorized = (
            request.user.is_superuser or 
            request.user.role == 'CENTER_MANAGER'
        )

        if is_authorized:
            return view_func(request, *args, **kwargs)
        
        # 3. Handle Unauthorized Access
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
             return JsonResponse({'error': 'Permission Denied'}, status=403)
        
        messages.error(request, "عذراً، هذه الصفحة مخصصة لمدراء المراكز فقط.")
        return redirect('centers:dashboard')
        
    return _wrapped_view
