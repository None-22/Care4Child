from django.db import models
from django.conf import settings

class NotificationLog(models.Model):
    """
    سجل الإشعارات - Notification History
    يستخدم للمحاكاة (Simulation) وللتدقيق (Audit Log)
    """
    NOTIFICATION_TYPES = (
        ('REMINDER', 'تذكير بموعد'),
        ('MISSED', 'تنبيه تأخير'),
        ('SYSTEM', 'إشعار نظام'),
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="المستلم", related_name="notifications")
    title = models.CharField(max_length=255, verbose_name="عنوان الإشعار")
    body = models.TextField(verbose_name="نص الإشعار")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='SYSTEM', verbose_name="نوع الإشعار")
    
    # حالة الإرسال (للمحاكاة ولـ FCM الحقيقي)
    sent_via_fcm = models.BooleanField(default=False, verbose_name="تم الإرسال عبر FCM؟")
    fcm_response = models.TextField(blank=True, null=True, verbose_name="رد سيرفر FCM")
    
    is_read = models.BooleanField(default=False, verbose_name="مقروءة؟")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت الإرسال")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "سجل إشعار"
        verbose_name_plural = "سجل الإشعارات"

    def __str__(self):
        return f"{self.title} -> {self.recipient.username}"
