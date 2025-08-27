from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, Student, Teacher, Skill, Schedule, Mark, 
    Resource, Request, Language, Session, Payment, Certificate, 
    Evaluation, Notification, Comment
)


# Personnalisation de l'affichage de CustomUser dans l'admin
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        ("🧑‍💼  Informations Personnelles", {
            "fields": ("username", "email", "first_name", "last_name"),
        }),
        ("🎭 Permissions", {
            "fields": ("role", "is_active", "is_staff", "is_superuser"),
        }),
         ("📅 Dates Importantes", {
            "fields": ("last_login", "date_joined"),
        }),
    )
    
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")

    def display_profile_picture(self, obj):
        if obj.profile_picture:
            return f'<img src="{obj.profile_picture.url}" width="50" height="50" />'
        return 'Aucune image'
    display_profile_picture.short_description = 'Photo de profil'
    display_profile_picture.allow_tags = True   
    
# Enregistrement des modèles dans Django Admin
admin.site.register(Student)
admin.site.register(Teacher)
admin.site.register(Skill)
admin.site.register(Language)

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher', 'language', 'date', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'language', 'date', 'teacher')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'teacher__user__first_name', 'teacher__user__last_name')
    date_hierarchy = 'date'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount', 'hours_purchased', 'payment_type', 'status', 'payment_date')
    list_filter = ('status', 'payment_type', 'payment_date')
    search_fields = ('student__user__first_name', 'student__user__last_name')

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('student', 'language', 'level', 'issued_date', 'is_active')
    list_filter = ('language', 'level', 'is_active', 'issued_date')
    search_fields = ('student__user__first_name', 'student__user__last_name')

@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher', 'language', 'evaluation_type', 'score', 'evaluation_date')
    list_filter = ('evaluation_type', 'language', 'evaluation_date')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'teacher__user__first_name', 'teacher__user__last_name')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('uploaded_by', 'title', 'resource_type', 'created_at')
    list_filter = ('uploaded_by', 'resource_type')
    fields = ('uploaded_by', 'title', 'description', 'file', 'url', 'resource_type', 'languages')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('student', 'request_type', 'subject', 'status', 'created_at')
    list_filter = ('student', 'request_type', 'status')
    fields = ('student', 'request_type', 'subject', 'description', 'attachment', 'status', 'response')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display = ('student', 'skill', 'mark')
    list_filter = ('student', 'skill', 'mark')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('day', 'teacher', 'skill', 'start_time', 'end_time', 'classroom','student')
    list_filter = ('day', 'teacher', 'skill','student')


@admin.register(Comment)
class Comment(admin.ModelAdmin):
    list_display = ('comment', 'student', 'teacher', 'language', 'comment_at')
    list_filter = ('student', 'teacher', 'language')
    fields = ('comment', 'student', 'teacher', 'language')
