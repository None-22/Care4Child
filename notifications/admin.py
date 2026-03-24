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
            return format_html('<span style="color: green;"><i class="fas fa-check-circle"></i> Sent</span>')
        return format_html('<span style="color: red;"><i class="fas fa-times-circle"></i> Failed</span>')
    status_badge.short_description = "Status"