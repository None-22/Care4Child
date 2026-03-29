from rest_framework import permissions

class IsCenterStaffOrReadOnly(permissions.BasePermission):
    """
    حارس بوابة: الموظف يكتب ويعدل، والعائلة تقرأ فقط.
    """
    def has_permission(self, request, view):
        # 1. التحقق من صلاحية المركز (تطبق على الموظفين فقط لحماية وصول العائلات)
        if request.user.is_authenticated and not request.user.is_superuser:
            if hasattr(request.user, 'role') and request.user.role in ['CENTER_MANAGER', 'CENTER_STAFF']:
                if hasattr(request.user, 'health_center') and request.user.health_center:
                    if not request.user.health_center.is_active:
                        return False

        # 2. إذا كان الطلب (GET)، مسموح للكل (لكن الفلترة في get_queryset ستحمي البيانات)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 3. إذا كان الطلب (POST, PUT, DELETE)، مسموح فقط للموظفين والمدراء
        return (
            request.user.is_authenticated and 
            (request.user.is_superuser or request.user.role in ['CENTER_MANAGER', 'CENTER_STAFF'])
        )


class IsAdminOrMinistry(permissions.BasePermission):
    """
    يسمح للسوبر أدمن أو موظفي الوزارة (MINISTRY role) بالعمليات.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or getattr(request.user, 'role', None) == 'MINISTRY')
        )
