from django.contrib import admin
from .models import Vaccine, VaccineSchedule, Child, VaccineRecord, Family, ChildVaccineSchedule
admin.site.register(VaccineSchedule)
class VaccineScheduleInline(admin.TabularInline):
    model = VaccineSchedule
    extra = 1

@admin.register(Vaccine)
class VaccineAdmin(admin.ModelAdmin):
    list_display = ('name_ar', 'name_en')
    inlines = [VaccineScheduleInline]

@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ('access_code', 'father_name', 'mother_name', 'created_at')
    search_fields = ('access_code', 'father_name', 'mother_name')
    readonly_fields = ('access_code',)

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'family', 'gender', 'date_of_birth', 'health_center', 'is_completed')
    list_filter = ('gender', 'is_completed', 'health_center', 'birth_governorate')
    search_fields = ('full_name', 'family__father_name', 'family__mother_name', 'family__access_code')
    autocomplete_fields = ['family', 'health_center']

@admin.register(ChildVaccineSchedule)
class ChildVaccineScheduleAdmin(admin.ModelAdmin):
    list_display = ('child', 'vaccine_schedule', 'due_date', 'is_taken')
    list_filter = ('is_taken', 'due_date')
    search_fields = ('child__full_name', 'child__family__access_code')

@admin.register(VaccineRecord)
class VaccineRecordAdmin(admin.ModelAdmin):
    list_display = ('child', 'vaccine', 'dose_number', 'date_given', 'staff')
    list_filter = ('vaccine', 'date_given')
    search_fields = ('child__full_name', 'child__family__access_code')