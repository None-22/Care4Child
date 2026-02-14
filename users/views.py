from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from .forms import CenterLoginForm

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    form_class = CenterLoginForm
    redirect_authenticated_user = True

def logout_view(request):
    """
    Custom logout view to handle GET requests for logout.
    Django 5.0+ requires POST by default, but this wrapper allows GET
    to support simple links in the UI.
    """
    logout(request)
    return redirect('login')
