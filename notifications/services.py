import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
import os
from .models import NotificationLog
from users.models import CustomUser

logger = logging.getLogger(__name__)

# --- Initialize Firebase App (Safe Singleton) ---
try:
    # 1. Path to serviceAccountKey.json
    # يفضل وضعه في مجلد آمن خارج الكود أو في الـ root
    cred_path = os.path.join(settings.BASE_DIR, 'serviceAccountKey.json')
    
    if os.path.exists(cred_path):
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin Initialized Successfully ✅")
        FIREBASE_READY = True
    else:
        logger.warning(f"Firebase Key not found at {cred_path}. Running in SIMULATION MODE 🧪")
        FIREBASE_READY = False
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {e}")
    FIREBASE_READY = False


class FCMService:
    """
    خدمة إرسال الإشعارات عبر Firebase Cloud Messaging.
    تعمل بوضع "حقيقي" إذا توفر المفتاح، أو "محاكاة" إذا لم يتوفر.
    """

    @staticmethod
    def send_notification(user, title, body, notification_type='SYSTEM'):
        """
        إرسال إشعار لمستخدم معين.
        """
        if not user.fcm_token:
            logger.warning(f"Skipping notification for {user.username}: No FCM Token")
            NotificationLog.objects.create(
                recipient=user,
                title=title,
                body=body,
                notification_type=notification_type,
                sent_via_fcm=False,
                fcm_response="No FCM Token found for user"
            )
            return False

        # --- Real Sending (Firebase) ---
        if FIREBASE_READY:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    token=user.fcm_token,
                    data={
                        'type': notification_type,
                        'click_action': 'FLUTTER_NOTIFICATION_CLICK'
                    }
                )
                response = messaging.send(message)
                
                # Log Success
                NotificationLog.objects.create(
                    recipient=user,
                    title=title,
                    body=body,
                    notification_type=notification_type,
                    sent_via_fcm=True,
                    fcm_response=f"Success: {response}"
                )
                return True
                
            except Exception as e:
                # Log Failure
                logger.error(f"FCM Send Error: {e}")
                NotificationLog.objects.create(
                    recipient=user,
                    title=title,
                    body=body,
                    notification_type=notification_type,
                    sent_via_fcm=False,
                    fcm_response=f"Error: {str(e)}"
                )
                return False
        
        # --- Simulation Mode (Fallback) ---
        else:
            simulated_response = f"SIMULATION_MODE_ID_{user.id}"
            logger.info(f"Simulating FCM Send to {user.username}: {title}")
            
            NotificationLog.objects.create(
                recipient=user,
                title=title,
                body=body,
                notification_type=notification_type,
                sent_via_fcm=True, # نعتبره تم (محاكاة)
                fcm_response=f"Simulated (No Key): {simulated_response}"
            )
            return True

    @staticmethod
    def send_bulk_notification(users, title, body):
        """إرسال لمجموعة مستخدمين"""
        count = 0
        for user in users:
            if FCMService.send_notification(user, title, body):
                count += 1
        return count
