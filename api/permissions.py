from rest_framework import permissions

class IsCenterStaffOrReadOnly(permissions.BasePermission):
    """
    حارس بوابة: الموظف يكتب ويعدل، والعائلة تقرأ فقط.
    """
    def has_permission(self, request, view):
        # 1. إذا كان الطلب (GET)، مسموح للكل (لكن الفلترة في get_queryset ستحمي البيانات)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 2. إذا كان الطلب (POST, PUT, DELETE)، مسموح فقط للموظفين والمدراء
        return (
            request.user.is_authenticated and 
            (request.user.is_superuser or request.user.role in ['CENTER_MANAGER', 'CENTER_STAFF'])
        )
