from django.apps import AppConfig


class MedicalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'medical'
    verbose_name = "إدارة السجلات الطبية"

    def ready(self):
        import medical.signals
    verbose_name = 'السجلات الطبية'
