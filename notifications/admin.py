from django.contrib import admin
from .models import NotificationLog
from django.utils.html import format_html

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notification_type', 'status_badge', 'created_at')
    list_filter = ('notification_type', 'sent_via_fcm', 'created_at')
    search_fields = ('title', 'body', 'recipient__username', 'recipient__first_name')
    readonly_fields = ('created_at', 'status_badge')

    def status_badge(self, obj):
        if obj.sent_via_fcm:
            return format_html('<span style="color: green;">✔ Sent (Simulated)</span>')
        return format_html('<span style="color: red;">✖ Failed</span>')
    status_badge.short_description = "Status"
    
    # --- زر التشغيل اليدوي ---
    change_list_template = "admin/notifications/notificationlog_change_list.html"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('send-reminders/', self.admin_site.admin_view(self.send_reminders_view), name='send-reminders'),
        ]
        return custom_urls + urls

    def send_reminders_view(self, request):
        from django.core.management import call_command
        from django.contrib import messages
        from django.http import HttpResponseRedirect
        
        try:
            call_command('send_reminders')
            self.message_user(request, "تم تشغيل محرك الإشعارات بنجاح! 🚀", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"حدث خطأ: {e}", level=messages.ERROR)
            
        return HttpResponseRedirect("../")
