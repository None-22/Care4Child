from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .decorators import ministry_required


@login_required
@ministry_required
def dashboard_view(request):
    """
    Ministry National Dashboard.
    Renders a shell — all data fetched client-side from /api/dashboard/stats/
    """
    return render(request, 'ministry/dashboard.html')


@login_required
@ministry_required
def health_centers_view(request):
    """
    Ministry Health Centers management page.
    Lists all centers. Add/Edit via API (AJAX).
    """
    return render(request, 'ministry/health_centers.html')


@login_required
@ministry_required
def governorates_view(request):
    """
    Ministry Governorates & Directorates management.
    Lists and allows adding governorates/directorates via API.
    """
    return render(request, 'ministry/governorates.html')


@login_required
@ministry_required
def vaccines_view(request):
    """
    Ministry Vaccines management page.
    Lists all registered vaccines. Add new via API.
    """
    return render(request, 'ministry/vaccines.html')


@login_required
@ministry_required
def children_view(request):
    """
    Ministry national children registry.
    Read-only view of all children across all centers.
    """
    return render(request, 'ministry/children.html')


@login_required
@ministry_required
def users_view(request):
    """
    Ministry system users overview.
    Lists all users with their roles.
    """
    return render(request, 'ministry/users.html')


@login_required
@ministry_required
def reports_view(request):
    """
    Ministry national reports page.
    Coverage reports per center, pie charts, exportable data.
    """
    return render(request, 'ministry/reports.html')
