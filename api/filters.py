import django_filters
from django.db.models import F
from medical.models import Child
from datetime import date
from dateutil.relativedelta import relativedelta

class ChildFilter(django_filters.FilterSet):
    # فلترات شخصية للطفل فقط
    gender = django_filters.CharFilter(field_name='gender')
    is_completed = django_filters.BooleanFilter(field_name='is_completed')
    health_center = django_filters.NumberFilter(field_name='health_center__id')
    governorate = django_filters.NumberFilter(field_name='health_center__governorate__id')
    directorate = django_filters.NumberFilter(field_name='health_center__directorate__id')
    
    # فلترات تاريخ الميلاد
    birth_year = django_filters.NumberFilter(field_name='date_of_birth__year')
    birth_month = django_filters.NumberFilter(field_name='date_of_birth__month')
    
    # فلتر حسب العمر بالأشهر (مثلاً الأطفال الذين يبلغون 6 أشهر)
    age_in_months = django_filters.NumberFilter(method='filter_by_age_months')

    class Meta:
        model = Child
        fields = ['gender', 'is_completed', 'health_center', 'governorate', 'directorate', 'birth_year', 'birth_month']

    def filter_by_age_months(self, queryset, name, value):
        """
        يُفلتر الأطفال الذين يبلغ عمرهم حالياً Value بالأشهر
        (مثلاً إذا أرسل 6، سيجلب كل من أكمل 6 أشهر ولم يكمل 7 أشهر)
        """
        try:
            value = int(value)
        except ValueError:
            return queryset
            
        today = date.today()
        
        # الطفل اللي عمره 6 أشهر ولد قبل 6 أشهر من اليوم
        # وحتى لا يتجاوز الـ 7 أشهر، يجب أن يكون تاريخ ميلاده:
        # بين (اليوم - 7 أشهر) و (اليوم - 6 أشهر)
        max_birth_date = today - relativedelta(months=value)
        min_birth_date = today - relativedelta(months=value + 1)
        
        # يعني تاريخ الميلاد > min_birth_date و <= max_birth_date
        return queryset.filter(date_of_birth__gt=min_birth_date, date_of_birth__lte=max_birth_date)