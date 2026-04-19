from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .decorators import ministry_required
from centers.models import CenterComplaint


@login_required
@ministry_required
def dashboard_view(request):
    """
    Ministry National Dashboard.
    Renders a shell — all data fetched client-side from /api/dashboard/stats/
    """
    pending_complaints_count = CenterComplaint.objects.filter(status='pending').count()
    return render(request, 'ministry/dashboard.html', {'pending_complaints_count': pending_complaints_count})


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
    Ministry Users Management Dashboard
    """
    return render(request, 'ministry/users.html')


@login_required
@ministry_required
def notifications_view(request):
    """
    Ministry Notifications List Page
    """
    return render(request, 'ministry/notifications.html')

import re
from django.shortcuts import get_object_or_404
from notifications.models import NotificationLog
from medical.models import Child

@login_required
@ministry_required
def notification_detail_view(request, pk):
    """
    Ministry Notification Detail Page (Marks as read and extracts child info)
    """
    notif = get_object_or_404(NotificationLog, pk=pk, recipient=request.user)
    
    if not notif.is_read:
        notif.is_read = True
        notif.save()
        
    # Try both storage formats (new: data-child-id, old: href="/center/child/ID/")
    child = None
    match = re.search(r'data-child-id="(\d+)"', notif.body)
    if not match:
        match = re.search(r'/center/child/(\d+)/', notif.body)
    
    if match:
        child_id = match.group(1)
        child = Child.objects.select_related(
            'health_center',
            'health_center__directorate',
            'health_center__directorate__governorate',
            'birth_governorate',
            'birth_directorate',
            'created_by',
        ).filter(id=child_id).first()
        
    return render(request, 'ministry/notification_detail.html', {
        'notification': notif,
        'child': child
    })


@login_required
@ministry_required
def reports_view(request):
    """
    Ministry national reports page.
    Coverage reports per center, pie charts, exportable data.
    """
    return render(request, 'ministry/reports.html')


@login_required
@ministry_required
def complaints_list_view(request):
    """
    Ministry Complaints List Page
    """
    complaints = CenterComplaint.objects.select_related('family', 'health_center').order_by('-created_at')
    
    context = {
        'complaints': complaints,
    }
    return render(request, 'ministry/complaints.html', context)
