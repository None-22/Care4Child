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

        # 3. Check Center Status
        if is_authorized and not request.user.is_superuser:
            if hasattr(request.user, 'health_center') and request.user.health_center:
                if not request.user.health_center.is_active:
                    from django.contrib.auth import logout
                    
                    if request.user.role == 'CENTER_STAFF':
                        error_msg = "عذراً، المركز الصحي التابع لك موقوف حالياً، ولذلك تم إيقاف صلاحية دخولك للنظام كموظف."
                    else:
                        error_msg = "عذراً، هذا المركز الصحي موقوف حالياً. لا يمكنك تسجيل الدخول."
                        
                    logout(request)
                    messages.error(request, error_msg)
                    return redirect('login')

        if is_authorized:
            return view_func(request, *args, **kwargs)
        
        # 3. Handle Unauthorized Access
        # Smart Handling: JSON for API/AJAX, Redirect for HTML
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
             return JsonResponse({'error': 'Permission Denied'}, status=403)
        
        if getattr(request.user, 'role', None) == 'MINISTRY':
            messages.error(request, "عذراً، هذه الصفحة مخصصة لموظفي المراكز فقط.")
            return redirect('ministry:dashboard')
            
        messages.error(request, "عذراً، تحتاج لتسجيل الدخول بحساب له صلاحيات.")
        return redirect('login')
        
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

        # 3. Check Center Status
        if is_authorized and not request.user.is_superuser:
            if hasattr(request.user, 'health_center') and request.user.health_center:
                if not request.user.health_center.is_active:
                    from django.contrib.auth import logout
                    
                    if request.user.role == 'CENTER_STAFF':
                        error_msg = "عذراً، المركز الصحي التابع لك موقوف حالياً، ولذلك تم إيقاف صلاحية دخولك للنظام كموظف."
                    else:
                        error_msg = "عذراً، هذا المركز الصحي موقوف حالياً. لا يمكنك تسجيل الدخول."
                        
                    logout(request)
                    messages.error(request, error_msg)
                    return redirect('login')

        if is_authorized:
            return view_func(request, *args, **kwargs)
        
        # 3. Handle Unauthorized Access
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
             return JsonResponse({'error': 'Permission Denied'}, status=403)
        
        if getattr(request.user, 'role', None) == 'MINISTRY':
            messages.error(request, "عذراً، هذه الصفحة مخصصة لمدراء المراكز فقط.")
            return redirect('ministry:dashboard')
            
        if getattr(request.user, 'role', None) == 'CENTER_STAFF':
            messages.error(request, "عذراً، هذه الصفحة مخصصة لمدراء المراكز فقط.")
            return redirect('centers:dashboard')

        messages.error(request, "عذراً، تحتاج لتسجيل الدخول بحساب له صلاحيات.")
        return redirect('login')
        
    return _wrapped_view
