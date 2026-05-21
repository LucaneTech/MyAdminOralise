from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, Student, Teacher,
    Resource, Request, Language, Session, Payment, Certificate,
    Evaluation, Notification, Comment, Profile, PaiementFormateur
)


# Personnalisation de l'affichage de CustomUser dans l'admin
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        ("Informations Personnelles", {
            "fields": ("username", "email", "first_name", "last_name"),
        }),
        ("Roles", {
            "fields": ("role", "is_active", "is_staff", "is_superuser"),
        }),
         ("Dates de connexion", {
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
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user__username','user__email', 'matricule', 'total_hours_used', 'statuts')
    list_filter = ('matricule','user','statuts')
    search_fields= ('user__first_name', 'user__last_name', 'matricule','statuts')


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'description')
    list_filter = ('name','code')
    search_fields= ('name', 'code')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'country', 'number', 'address', 'about')
    search_fields = ('user__username', 'user__email', 'city', 'country')
    list_filter = ('city', 'country')
     
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user__username','user__email', 'speciality', 'date_joined', 'statut')
    list_filter = ('statut', 'languages')
    search_fields = ('user__first_name', 'user__last_name', 'speciality' 'statut')



@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'language', 'date', 'type_seance', 'status', 'statut_validation', 'fiche_completee')
    list_filter = ('status', 'statut_validation', 'type_seance', 'language', 'date', 'teacher')
    search_fields = ('teacher__user__first_name', 'teacher__user__last_name', 'theme_cours')
    date_hierarchy = 'date'
    fieldsets = (
        ("Identification", {
            "fields": ("students", "teacher", "language", "date", "start_time", "end_time", "duree_minutes", "type_seance", "status", "meeting_link"),
        }),
        ("Contenu pédagogique", {
            "fields": ("theme_cours", "comp_oral", "comp_comprehension", "comp_ecrit", "comp_grammaire", "comp_vocabulaire"),
        }),
        ("Évaluation rapide", {
            "fields": ("participation", "comprehension_score", "engagement"),
        }),
        ("Analyse pédagogique", {
            "fields": ("difficultes", "observations_formateur", "prochaine_etape"),
        }),
        ("Devoir", {
            "fields": ("devoir_donne", "description_devoir"),
        }),
        ("Validation", {
            "fields": ("seance_realisee", "fiche_completee", "statut_validation"),
        }),
        ("Notes legacy", {
            "fields": ("notes", "feedback"),
            "classes": ("collapse",),
        }),
    )

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount', 'hours_purchased', 'payment_type', 'status', 'payment_date', 'languages')
    list_filter = ('status', 'payment_type', 'payment_date', 'languages')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'languages')

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('student', 'language', 'level', 'certificate_id', 'issued_date', 'is_active')
    list_filter = ('language', 'level', 'is_active', 'issued_date')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'certificate_id')
    readonly_fields = ('certificate_id', 'issued_date')
    fieldsets = (
        ("Informations de base", {
            "fields": ("student", "language", "level", "certificate_id", "issued_date", "certificate_file", "is_active"),
        }),
        ("Informations pédagogiques", {
            "fields": ("duree_formation", "competences_validees", "appreciation_pedagogique"),
        }),
    )

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
    list_display = ('teachers', 'title', 'resource_type', 'created_at')
    list_filter = ('teachers', 'resource_type')
    fields = ('teachers', 'title', 'description', 'file', 'url', 'resource_type', 'students', 'languages', 'is_visible')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('student', 'request_type', 'teacher', 'subject', 'status', 'created_at')
    list_filter = ('student', 'request_type', 'status')
    fields = ('student', 'request_type', 'teacher', 'subject', 'description', 'attachment', 'status', 'response')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Comment)
class Comment(admin.ModelAdmin):
    list_display = ('comment', 'student', 'teacher', 'language', 'comment_at')
    list_filter = ('student', 'teacher', 'language')
    fields = ('comment', 'student', 'teacher', 'language')


@admin.register(PaiementFormateur)
class PaiementFormateurAdmin(admin.ModelAdmin):
    list_display = ('formateur', 'montant', 'montant_calcule', 'periode_debut', 'periode_fin', 'statut', 'date_paiement')
    list_filter = ('statut', 'formateur', 'periode_debut')
    search_fields = ('formateur__user__first_name', 'formateur__user__last_name')
    readonly_fields = ('montant_calcule', 'created_at', 'updated_at')
    fieldsets = (
        ("Formateur & Période", {
            "fields": ("formateur", "periode_debut", "periode_fin"),
        }),
        ("Paiement", {
            "fields": ("montant", "montant_calcule", "statut", "date_paiement", "commentaire"),
        }),
    )
