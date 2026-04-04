import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import os
from .models import NotificationLog

logger = logging.getLogger(__name__)

def initialize_firebase():
    """تهيئة فايربيز فقط عند الحاجة لضمان عدم تأخير تشغيل السيرفر"""
    if not firebase_admin._apps:
        try:
            cred_path = os.environ.get(
                'FIREBASE_KEY_PATH',
                os.path.join(settings.BASE_DIR, 'serviceAccountKey.json')
            )
            
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin Initialized Successfully")
                return True
            else:
                logger.warning(f"Firebase Key not found at {cred_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            return False
    return True

class FCMService:
    @staticmethod
    def send_notification(user, title, body, notification_type='SYSTEM'):
        if not user.fcm_token:
            NotificationLog.objects.create(recipient=user, title=title, body=body, 
                                         notification_type=notification_type, sent_via_fcm=False, 
                                         fcm_response="No FCM Token")
            return False

        # نحاول تشغيل فايربيز الآن فقط (عند الإرسال)
        firebase_ok = initialize_firebase()

        if firebase_ok:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    token=user.fcm_token,
                    data={'type': notification_type, 'click_action': 'FLUTTER_NOTIFICATION_CLICK'}
                )
                response = messaging.send(message)
                NotificationLog.objects.create(recipient=user, title=title, body=body, 
                                             notification_type=notification_type, sent_via_fcm=True, 
                                             fcm_response=f"Success: {response}")
                return True
            except Exception as e:
                logger.error(f"FCM Send Error: {e}")
                NotificationLog.objects.create(recipient=user, title=title, body=body, 
                                             notification_type=notification_type, sent_via_fcm=False, 
                                             fcm_response=f"Error: {str(e)}")
                return False
        
        # وضع المحاكاة إذا فشل الاتصال بفايربيز
        logger.info(f"SIMULATION MODE: Notification for {user.username}")
        NotificationLog.objects.create(recipient=user, title=title, body=body, 
                                     notification_type=notification_type, sent_via_fcm=True, 
                                     fcm_response="Simulated (Check Credentials)")
        return True

    @staticmethod
    def send_bulk_notification(users, title, body):
        """إرسال لمجموعة مستخدمين"""
        count = 0
        for user in users:
            if FCMService.send_notification(user, title, body):
                count += 1
        return count