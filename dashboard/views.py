import csv
from multiprocessing import context
from urllib import request
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import Http404, JsonResponse
from datetime import date, datetime, timedelta
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST, require_GET
from django.template.loader import render_to_string



from dashboard import models
from dashboard.decorators import admin_required
from dashboard.models import (
    CustomUser,
    Student,
    Teacher,
    Profile,
    Language,
    Schedule,
    Resource,
    Request,
    Assignment,
    Submission,
    Session,
    Payment,
    Certificate,
    Evaluation,
    Notification,
    Comment,
)
from .forms import ProfileUpdateForm, SessionForm, ResourceForm, ResourceFilterForm, BulkAssignForm
 
import json


def custom_404_view(request, exception):
    return render(request, "404.html", status=404)


@login_required
def dashboard_view(request, username=None):
    print(
        f"DEBUG: dashboard_view called - username: {username}, user role: {request.user.role}"
    )
    # Si aucun username n'est fourni, utiliser celui de l'utilisateur connecté
    if username is None:
        username = request.user.username
        print(f"DEBUG: username set to: {username}")
    # If user is a teacher, redirect to teacher_view
    if request.user.role == "teacher":
        print(f"DEBUG: Redirecting teacher to teacher_view")
        return redirect("teacher_view", username=username)

    # if user'role is preUser
    if request.user.role == "admin":
        return redirect("admin_dashboard")

    try:
        # Vérifier si l'utilisateur demandé existe
        requested_user = CustomUser.objects.filter(username=username).first()
        if not requested_user:
            raise Http404("Utilisateur non trouvé.")
        profile = Profile.objects.filter(user=requested_user).first()
        if not profile:
            raise Http404("Profil non trouvé.")

        # Remplacez get_object_or_404 par .filter().first()

        # Vérifier si l'utilisateur est un étudiant
        if requested_user.role != "student":
            raise Http404("Cette page est réservée aux étudiants.")

        student = Student.objects.filter(user=requested_user).first()
        total_sessions = Session.objects.filter(student=student).count()
        context = {
            "total_sessions": total_sessions,
            "profile": profile,
            "user": request.user,
            "username": username,
        }

        student = Student.objects.filter(user=requested_user).first()
        today = timezone.now().date()

        # Informations principales selon le cahier des charges
        context.update(
            {
                "student": student,
                "hours_remaining": student.hours_remaining,
                "total_hours_purchased": student.total_hours_purchased,
                "total_hours_used": student.total_hours_used,
                "languages": student.languages.all(),
                "current_teachers": student.current_teachers.all(),
            }
        )

        # Planning personnel (séances à venir)
        upcoming_sessions = Session.objects.filter(
            student=student, date__gte=today, status="scheduled"
        ).order_by("date", "start_time")
        context["upcoming_sessions"] = upcoming_sessions

        # Historique des séances (faites / reportées)
        completed_sessions = Session.objects.filter(
            student=student, status="completed"
        ).order_by("-date")[:10]
        context["completed_sessions"] = completed_sessions

        rescheduled_sessions = Session.objects.filter(
            student=student, status="rescheduled"
        ).order_by("-date")[:5]
        context["rescheduled_sessions"] = rescheduled_sessions

        # Séances du jour
        today_sessions = Session.objects.filter(student=student, date=today).order_by(
            "start_time"
        )
        context["today_sessions"] = today_sessions

        # Notifications non lues
        unread_notifications = Notification.objects.filter(
            user=request.user, is_read=False
        ).order_by("-created_at")[:5]
        context["unread_notifications"] = unread_notifications

        # Certificats récents
        recent_certificates = Certificate.objects.filter(
            student=student, is_active=True
        ).order_by("-issued_date")[:3]
        context["recent_certificates"] = recent_certificates

        # Évaluations récentes
        recent_evaluations = Evaluation.objects.filter(student=student).order_by(
            "-evaluation_date"
        )[:5]
        context["recent_evaluations"] = recent_evaluations

        # Statistiques de progression
        total_sessions = Session.objects.filter(student=student).count()
        completed_count = Session.objects.filter(
            student=student, status="completed"
        ).count()
        

        context.update(
            {
                "total_sessions": total_sessions,
                "completed_sessions_count": completed_count,
              
            }
        )

        return render(request, "dashboard/student/home/index.html", context)

    except Exception as e:
        context = {"error": str(e)}
        return render(request, "404.html", context)
    # except Exception as e:
    #     messages.error(request, f"Erreur lors du chargement du dashboard: {str(e)}")
    #     return redirect('dashboard_home')


@login_required
def teacher_view(request, username=None):
    if username is None:
        username = request.user.username

    try:
        requested_user = get_object_or_404(CustomUser, username=username)
        profile = get_object_or_404(Profile, user=requested_user)

        if requested_user.role != "teacher":
            raise Http404("Cette page est réservée aux enseignants.")

        teacher = get_object_or_404(Teacher, user=requested_user)
        today = timezone.now().date()

        # Informations principales
        context = {
            "profile": profile,
            "user": request.user,
            "username": username,
            "teacher": teacher,
            "languages": teacher.languages.all(),
            "total_students": Student.objects.filter(current_teachers=teacher).count(),
            "hourly_rate": teacher.hourly_rate,
           
        }

        # Emploi du temps avec filtres par langue
        selected_language = request.GET.get("language")
        today_sessions = Session.objects.filter(
            teacher=teacher, 
            date=today, 
            status="scheduled"
        )
        
        if selected_language:
            today_sessions = today_sessions.filter(language__code=selected_language)
        
        context["today_sessions"] = today_sessions.order_by("start_time")
        context["selected_language"] = selected_language

        # Séances de la semaine (remplacer teacher.weekly_sessions)
        end_of_week = today + timedelta(days=7)
        weekly_sessions = Session.objects.filter(
            teacher=teacher,
            date__gte=today,
            date__lte=end_of_week,
            status="scheduled"
        ).order_by("date", "start_time")
        context["weekly_sessions"] = weekly_sessions

        # Séances récentes (faites)
        recent_completed_sessions = Session.objects.filter(
            teacher=teacher, 
            status="completed"
        ).order_by("-date")[:10]
        context["recent_completed_sessions"] = recent_completed_sessions

        # Séances à cocher (prévues pour aujourd'hui)
        sessions_to_check = Session.objects.filter(
            teacher=teacher, 
            date=today, 
            status="scheduled"
        ).order_by("start_time")
        context["sessions_to_check"] = sessions_to_check

        # Séances reportées
        rescheduled_sessions = Session.objects.filter(
            teacher=teacher, 
            status="rescheduled"
        ).order_by("-date")[:5]
        context["rescheduled_sessions"] = rescheduled_sessions

        # Statistiques par langue
        language_stats = []
        for language in teacher.languages.all():
            sessions_count = Session.objects.filter(
                teacher=teacher, 
                language=language
            ).count()
            completed_count = Session.objects.filter(
                teacher=teacher, 
                language=language, 
                status="completed"
            ).count()
            students_count = Student.objects.filter(
                current_teachers=teacher, 
                languages=language
            ).count()

            language_stats.append(
                {
                    "language": language,
                    "total_sessions": sessions_count,
                    "completed_sessions": completed_count,
                    "students_count": students_count,
                    "completion_rate": (
                        (completed_count / sessions_count * 100)
                        if sessions_count > 0
                        else 0
                    ),
                }
            )
        context["language_stats"] = language_stats

        # Évaluations récentes
        recent_evaluations = Evaluation.objects.filter(
            teacher=teacher
        ).order_by("-evaluation_date")[:5]
        context["recent_evaluations"] = recent_evaluations

        # Notifications
        unread_notifications = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).order_by("-created_at")[:5]
        context["unread_notifications"] = unread_notifications

        return render(request, "dashboard/teacher/home/index.html", context)

    except Http404:
        raise
    except Exception as e:
        print(f"Error in teacher_view: {str(e)}")
        messages.error(
            request, 
            "Une erreur est survenue lors du chargement du tableau de bord."
        )
        return render(request, "404.html", {"error": str(e)}, status=500)


# Vue pour afficher le profil (version fonction)


def profile_view(request):
    user = get_object_or_404(CustomUser, username=request.user.username)
    profile = get_object_or_404(Profile, user=user)

    context = {
        "profile": profile,
        "user": user,
    }

    if user.role == "student":
        student = get_object_or_404(Student, user=user)
        total_sessions = Session.objects.filter(student=student).count()
        context = {
            "student": student,
            "total_sessions": total_sessions,
        }
        return render(request, "dashboard/student/home/profile.html", context)

    elif user.role == "teacher":
        teacher = get_object_or_404(Teacher, user=user)
        total_sessions = Session.objects.filter(teacher=teacher).count()
        context = {
            "teacher": teacher,
            "total_sessions": total_sessions,
        }
        return render(request, "dashboard/teacher/home/profile.html", context)
    


@login_required
def profile_edit(request):
    user = get_object_or_404(CustomUser, username=request.user.username)
    profile = get_object_or_404(Profile, user=user)

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("profile_view")
    else:
        form = ProfileUpdateForm(instance=profile)

    context = {
        "profile": profile,
        "form": form,
        "user": user,
    }

    if user.role == "teacher":
        return render(request, "dashboard/teacher/home/profile_edit.html", context)
    elif user.role == "student":
        return render(request, "dashboard/student/home/profile_edit.html", context)
    else:
        return render(request, "dashboard/default/profile_edit.html", context)


# Vue pour changer la photo de profil

# @login_required
# def update_profile_picture(request):
#     if request.method == 'POST':
#         profile = request.user.user_profile
#         profile.profile_picture = request.FILES.get('profile_picture')
#         profile.save()
#         return redirect('profile_view')
#     return render(request, 'profiles/update_picture.html')



def resources_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=request.user)
    context = {
        "profile": profile,
        "user": user,
        "username": request.user.username,
    }

    # Version corrigée
    if user.role == "student":
        student = get_object_or_404(Student, user=user)
        teachers = student.current_teachers.all()
        
        # Obtenir les langues de l'étudiant
        student_languages = student.languages.all()  # Supposons que Student a un champ languages
        
        now = timezone.now()
        
        resources = Resource.objects.filter(
            is_visible=True,
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=now)
        ).filter(
            # Logique d'accès basée sur le type d'accès
            Q(
                # Cas 1: Ressources accessibles à tous les étudiants
                Q(access_type='all_students') & 
                Q(teachers__in=teachers) &
                Q(languages__in=student_languages)  # Filtre par les langues de l'étudiant
            ) |
            # Cas 2: Ressources spécifiques à certains étudiants
            Q(
                Q(access_type='specific_students') &
                Q(students=student) &  # L'étudiant est dans la liste
                Q(teachers__in=teachers) &
                Q(languages__in=student_languages)
            ) 
         
        ).distinct()
        
        # Comptage pour statistiques
        total_resources = resources.count()
        recent_resources = resources.filter(created_at__gte=now - timezone.timedelta(days=7)).count()
        
        # Regrouper par type de ressource pour faciliter l'affichage
        resources_by_type = {}
        for resource in resources:
            resource_type = resource.resource_type
            if resource_type not in resources_by_type:
                resources_by_type[resource_type] = []
            resources_by_type[resource_type].append(resource)
        
        context.update({
            "resources": resources,
            "student": student,
            "total_resources": total_resources,
            "recent_resources": recent_resources,
            "resources_by_type": resources_by_type,
            "teachers": teachers,  # Pour afficher les enseignants si besoin
            "now": now,  # Pour vérifier les dates d'expiration dans le template
        })
    
        return render(request, "dashboard/student/home/resources.html", context)


@login_required
def teacher_resources_dashboard(request):
   
    user = request.user
    if user.role != "teacher":
        return redirect('dashboard')
    
    teacher = get_object_or_404(Teacher, user=user)
    
    # Variables d'action
    action = request.GET.get('action', 'list')
    resource_id = request.GET.get('id')
    student_id = request.GET.get('student_id')
    
    # Récupérer les données nécessaires
    students = Student.objects.filter(current_teachers=teacher)
    languages = Language.objects.filter(teachers=teacher)
    
    # Base queryset
    resources = Resource.objects.filter(teachers=teacher)
    
    # Gestion des actions
    if request.method == 'POST':
        return handle_post_actions(request, teacher, action, resource_id)
    
    # Filtrage GET
    resources = apply_filters(request, resources)
    
    # Préparer le contexte
    context = {
        'teacher': teacher,
        'students': students,
        'languages': languages,
        'resources': resources.order_by('-created_at'),
        'current_action': action,
        'resource_types': Resource.RESOURCE_TYPES,
        'access_types': Resource.ACCESS_TYPES,
        'now': timezone.now(),
        
        # Données pour les modals
        'selected_resource': None,
        'selected_student': None,
        'form': None,
        'bulk_form': None,
    }
    
    # Préparer les données selon l'action
    if action == 'create':
        context['form'] = ResourceForm(teacher=teacher)
    elif action == 'edit' and resource_id:
        resource = get_object_or_404(Resource, id=resource_id, teachers=teacher)
        context['selected_resource'] = resource
        context['form'] = ResourceForm(instance=resource, teacher=teacher)
    elif action == 'assign' and resource_id:
        resource = get_object_or_404(Resource, id=resource_id, teachers=teacher)
        context['selected_resource'] = resource
        context['bulk_form'] = BulkAssignForm(teacher=teacher, initial={'students': resource.students.all()})
    elif action == 'create_for_student' and student_id:
        student = get_object_or_404(Student, id=student_id, current_teachers=teacher)
        context['selected_student'] = student
        initial = {
            'access_type': 'specific_students',
            'students': [student]
        }
        context['form'] = ResourceForm(teacher=teacher, initial=initial)
    
    return render(request, 'dashboard/teacher/home/resources.html', context)


def handle_post_actions(request, teacher, action, resource_id):
    """Gère toutes les actions POST"""
    if action == 'create':
        return create_resource(request, teacher)
    elif action == 'edit' and resource_id:
        return edit_resource(request, teacher, resource_id)
    elif action == 'delete' and resource_id:
        return delete_resource(request, teacher, resource_id)
    elif action == 'assign' and resource_id:
        return assign_resource(request, teacher, resource_id)
    elif action == 'toggle_visibility' and resource_id:
        return toggle_visibility(request, teacher, resource_id)
    elif action == 'bulk_assign':
        return bulk_assign_resources(request, teacher)
    
    return redirect('teacher_resources_dashboard')


def create_resource(request, teacher):
    """Créer une nouvelle ressource"""
    form = ResourceForm(request.POST, request.FILES, teacher=teacher)
    
    if form.is_valid():
        resource = form.save(commit=False)
        resource.teachers = teacher
        resource.save()
        form.save_m2m()  # Pour les relations ManyToMany
        
        messages.success(request, 'Ressource créée avec succès!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Ressource créée avec succès!'})
        return redirect('teacher_resources_dashboard')
    
    # Si erreur et requête AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'errors': form.errors})
    
    messages.error(request, 'Erreur lors de la création de la ressource')
    return redirect('teacher_resources_dashboard?action=create')


def edit_resource(request, teacher, resource_id):
    """Modifier une ressource existante"""
    resource = get_object_or_404(Resource, id=resource_id, teachers=teacher)
    form = ResourceForm(request.POST, request.FILES, instance=resource, teacher=teacher)
    
    if form.is_valid():
        form.save()
        messages.success(request, 'Ressource modifiée avec succès!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Ressource modifiée avec succès!'})
        return redirect('teacher_resources_dashboard')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'errors': form.errors})
    
    messages.error(request, 'Erreur lors de la modification de la ressource')
    return redirect(f'teacher_resources_dashboard?action=edit&id={resource_id}')


def delete_resource(request, teacher, resource_id):
    """Supprimer une ressource"""
    resource = get_object_or_404(Resource, id=resource_id, teachers=teacher)
    
    if request.method == 'POST':
        resource.delete()
        messages.success(request, 'Ressource supprimée avec succès!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Ressource supprimée avec succès!'})
    
    return redirect('teacher_resources_dashboard')


def assign_resource(request, teacher, resource_id):
    """Assigner une ressource à des étudiants"""
    resource = get_object_or_404(Resource, id=resource_id, teachers=teacher)
    
    if request.method == 'POST':
        student_ids = request.POST.getlist('students')
        students = Student.objects.filter(id__in=student_ids, current_teachers=teacher)
        
        resource.students.clear()
        resource.students.add(*students)
        
        # Si on assigne des étudiants spécifiques, changer le type d'accès
        if students.exists():
            resource.access_type = 'specific_students'
        else:
            resource.access_type = 'all_students'
        
        resource.save()
        
        messages.success(request, f'Ressource assignée à {students.count()} étudiant(s)')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Assignation réussie à {students.count()} étudiant(s)'})
    
    return redirect('teacher_resources_dashboard')


def toggle_visibility(request, teacher, resource_id):
    """Activer/désactiver la visibilité d'une ressource"""
    resource = get_object_or_404(Resource, id=resource_id, teachers=teacher)
    
    if request.method == 'POST':
        resource.is_visible = not resource.is_visible
        resource.save()
        
        status = "visible" if resource.is_visible else "masquée"
        messages.success(request, f'Ressource {status} avec succès!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'message': f'Ressource {status}',
                'is_visible': resource.is_visible
            })
    
    return redirect('teacher_resources_dashboard')


def bulk_assign_resources(request, teacher):
    """Assigner plusieurs ressources à plusieurs étudiants"""
    if request.method == 'POST':
        resource_ids = request.POST.getlist('resources')
        student_ids = request.POST.getlist('students')
        
        resources = Resource.objects.filter(id__in=resource_ids, teachers=teacher)
        students = Student.objects.filter(id__in=student_ids, current_teachers=teacher)
        
        for resource in resources:
            resource.students.add(*students)
            if students.exists():
                resource.access_type = 'specific_students'
                resource.save()
        
        messages.success(request, f'{resources.count()} ressource(s) assignée(s) à {students.count()} étudiant(s)')
    
    return redirect('teacher_resources_dashboard')


def apply_filters(request, queryset):
    """Appliquer les filtres sur le queryset"""
    filters = {}
    
    # Filtre par type de ressource
    resource_type = request.GET.get('resource_type')
    if resource_type:
        queryset = queryset.filter(resource_type=resource_type)
        filters['resource_type'] = resource_type
    
    # Filtre par langue
    language_id = request.GET.get('language')
    if language_id:
        queryset = queryset.filter(languages__id=language_id)
        filters['language'] = language_id
    
    # Filtre par étudiant
    student_id = request.GET.get('student')
    if student_id:
        queryset = queryset.filter(students__id=student_id)
        filters['student'] = student_id
    
    # Filtre par type d'accès
    access_type = request.GET.get('access_type')
    if access_type:
        queryset = queryset.filter(access_type=access_type)
        filters['access_type'] = access_type
    
    # Filtre par visibilité
    is_visible = request.GET.get('is_visible')
    if is_visible in ['true', 'false']:
        queryset = queryset.filter(is_visible=(is_visible == 'true'))
        filters['is_visible'] = is_visible
    
    # Filtre par date
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)
        filters['date_from'] = date_from
    
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)
        filters['date_to'] = date_to
    
    # Recherche texte
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
        filters['search'] = search
    
    return queryset.distinct()


# API pour charger les détails d'une ressource (pour AJAX)
@login_required
@require_GET
def get_resource_details(request, resource_id):
    """API pour récupérer les détails d'une ressource en JSON (pour AJAX)"""
    user = request.user
    if user.role != "teacher":
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    teacher = get_object_or_404(Teacher, user=user)
    resource = get_object_or_404(Resource, id=resource_id, teachers=teacher)
    
    data = {
        'id': resource.id,
        'title': resource.title,
        'description': resource.description,
        'resource_type': resource.resource_type,
        'resource_type_display': resource.get_resource_type_display(),
        'access_type': resource.access_type,
        'access_type_display': resource.get_access_type_display(),
        'file_url': resource.file.url if resource.file else None,
        'url': resource.url,
        'is_visible': resource.is_visible,
        'valid_until': resource.valid_until.strftime('%Y-%m-%d %H:%M') if resource.valid_until else None,
        'created_at': resource.created_at.strftime('%d/%m/%Y %H:%M'),
        'languages': [{'id': lang.id, 'name': lang.name} for lang in resource.languages.all()],
        'students': [{'id': stu.id, 'name': stu.user.get_full_name()} for stu in resource.students.all()],
    }
    
    return JsonResponse(data)


# API pour charger le formulaire (pour AJAX)
@login_required
@require_GET
def get_resource_form(request):
    """API pour récupérer le formulaire en HTML (pour AJAX)"""
    user = request.user
    if user.role != "teacher":
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    teacher = get_object_or_404(Teacher, user=user)
    resource_id = request.GET.get('resource_id')
    student_id = request.GET.get('student_id')
    
    if resource_id:
        # Édition
        resource = get_object_or_404(Resource, id=resource_id, teachers=teacher)
        form = ResourceForm(instance=resource, teacher=teacher)
        action = 'edit'
    elif student_id:
        # Création pour un étudiant spécifique
        student = get_object_or_404(Student, id=student_id, current_teachers=teacher)
        initial = {
            'access_type': 'specific_students',
            'students': [student]
        }
        form = ResourceForm(teacher=teacher, initial=initial)
        action = 'create_for_student'
    else:
        # Création normale
        form = ResourceForm(teacher=teacher)
        action = 'create'
    
    from django.template.loader import render_to_string
    html = render_to_string('dashboard/teacher/resources/includes/resource_form_modal.html', {
        'form': form,
        'action': action,
        'teacher': teacher,
    })
    
    return JsonResponse({'html': html})


@login_required
def resources_add(request):
    user = request.user
    if not hasattr(user, "teacher"):
        messages.error(request, "Page réservée aux enseignants.")
        return redirect("dashboard_home")
    teacher = get_object_or_404(Teacher, user=user)
    teacher_languages = Language.objects.filter(teachers=teacher)
    if request.method == "POST":
        form = ResourceForm(request.POST, request.FILES)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.teachers = user
            resource.save()
            # Ajoute les languages sélectionnés (liés à la branch)
            form.save_m2m()
            return redirect("teacher_resources")
    else:
        form = ResourceForm()
        # Limite les languages proposés à ceux du teacher
        form.fields["languages"].queryset = teacher_languages
    context = {
        "form": form,
        "teacher": teacher,
    }
    return render(request, "dashboard/teacher/home/resources_add.html", context)


@login_required
def requests_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    context = {
        "profile": profile,
        "user": user,
        "username": user.username,
    }

    # ----- for students -----
    if user.role == "student":
        student = get_object_or_404(Student, user=user)

        # Création d'une nouvelle demande
        if request.method == "POST":
            teacher_id = request.POST.get("teacher_id")
            request_type = request.POST.get("request_type")
            subject = request.POST.get("subject")
            description = request.POST.get("description")
            attachment = request.FILES.get("attachme    nt")

            teacher = None
            if teacher_id:
                teacher = get_object_or_404(Teacher, id=teacher_id)
            else:
                messages.error(
                    request, "Veuillez sélectionner un enseignant destinataire."
                )
                return redirect("requests_view")

            Request.objects.create(
                student=student,
                teacher=teacher,
                request_type=request_type,
                subject=subject,
                description=description,
                attachment=attachment,
            )
            return redirect("requests_view")

        # Toutes les demandes de l'étudiant
        requests = Request.objects.filter(student=student)
        teachers = student.current_teachers.all()
        context.update(
            {
                "teachers": teachers,
                "student": student,
                "requests": requests,
                "total_requests": requests.count(),
                "pending_requests": requests.filter(status="pending").count(),
                "approved_requests": requests.filter(status="approved").count(),
                "rejected_requests": requests.filter(status="rejected").count(),
            }
        )

        return render(request, "dashboard/student/home/requests.html", context)

    # ----- for teachers (optional) -----
    elif user.role == "teacher":
        teacher = get_object_or_404(Teacher, user=user)
        # Toutes les demandes des étudiants liés à cet enseignant
        requests = Request.objects.filter(student__current_teachers=teacher)
        total_request = requests.count() if requests else 0
        context.update(
            {
                "teacher": teacher,
                "requests": requests,
                "total_requests": total_request,
                "pending_requests": requests.filter(status="pending").count(),
                "processing_requests": requests.filter(status="processing").count(),
                "approved_requests": requests.filter(status="approved").count(),
                "rejected_requests": requests.filter(status="rejected").count(),
            }
        )

        return render(request, "dashboard/teacher/home/requests.html", context)



@login_required
@require_POST
def update_request_status(request):
    """Vue AJAX pour mettre à jour le statut d'une demande"""
    try:
        # Récupérer les données POST
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')
        
        # Vérifier que l'utilisateur est un enseignant
        if request.user.role != "teacher":
            return JsonResponse({
                'success': False,
                'error': 'Accès réservé aux enseignants'
            }, status=403)
        
        # Récupérer l'enseignant connecté
        teacher = Teacher.objects.get(user=request.user)
        
        # Récupérer la demande (vérifier qu'elle appartient à cet enseignant)
        req = Request.objects.get(id=request_id, teacher=teacher)
        
        # Mettre à jour le statut selon l'action
        status_map = {
            'process': 'processing',
            'approve': 'approved', 
            'reject': 'rejected',
            'pending': 'pending'
        }
        
        if action not in status_map:
            return JsonResponse({
                'success': False,
                'error': 'Action invalide'
            }, status=400)
        
        req.status = status_map[action]
        req.save()
        
        # Récupérer les nouvelles statistiques
        teacher_requests = Request.objects.filter(teacher=teacher)
        stats = {
            'total': teacher_requests.count(),
            'pending': teacher_requests.filter(status='pending').count(),
            'processing': teacher_requests.filter(status='processing').count(),
            'approved': teacher_requests.filter(status='approved').count(),
            'rejected': teacher_requests.filter(status='rejected').count(),
        }
        
        return JsonResponse({
            'success': True,
            'message': f'Statut mis à jour : {req.get_status_display()}',
            'request': {
                'id': req.id,
                'status': req.status,
                'status_display': req.get_status_display(),
            },
            'stats': stats
        })
        
    except Teacher.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Enseignant non trouvé'
        }, status=404)
        
    except Request.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Demande non trouvée ou non autorisée'
        }, status=404)
        
    except Exception as e:
        # Pour déboguer, affichez l'erreur
        import traceback
        print(f"Erreur update_request_status: {e}")
        print(traceback.format_exc())
        
        return JsonResponse({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }, status=500)

@login_required
@require_POST
def add_request_response(request):
    """Vue AJAX pour ajouter une réponse à une demande"""
    try:
        # Récupérer les données POST
        request_id = request.POST.get('request_id')
        response_text = request.POST.get('response', '').strip()
        
        # Vérifications
        if request.user.role != "teacher":
            return JsonResponse({
                'success': False,
                'error': 'Accès réservé aux enseignants'
            }, status=403)
        
        if not response_text:
            return JsonResponse({
                'success': False,
                'error': 'Le message de réponse est requis'
            }, status=400)
        
        # Récupérer l'enseignant et la demande
        teacher = Teacher.objects.get(user=request.user)
        req = Request.objects.get(id=request_id, teacher=teacher)
        
        # Ajouter la réponse
        req.response = response_text
        req.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Réponse envoyée avec succès',
            'request_id': req.id,
            'response': response_text
        })
        
    except Teacher.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Enseignant non trouvé'
        }, status=404)
        
    except Request.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Demande non trouvée ou non autorisée'
        }, status=404)
        
    except Exception as e:
        import traceback
        print(f"Erreur add_request_response: {e}")
        print(traceback.format_exc())
        
        return JsonResponse({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }, status=500)


def settings_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    if request.method == "POST":
        # Traitement des paramètres
        theme = request.POST.get("theme", "light")
        language = request.POST.get("language", "fr")
        notifications = request.POST.get("notifications", "all")
        email_notifications = request.POST.get("email_notifications", "true")

        # Sauvegarder le thème dans la base de données
        profile.theme_preference = theme
        profile.save()

        # Sauvegarder les autres préférences dans la session
        request.session["language"] = language
        request.session["notifications"] = notifications
        request.session["email_notifications"] = email_notifications

        # Rediriger vers la même page
        return redirect("settings_view")

    # Récupérer les paramètres actuels
    context = {
        "profile": profile,
        "user": user,
        "username": user.username,
        "current_theme": profile.theme_preference,
        "current_language": request.session.get("language", "fr"),
        "current_notifications": request.session.get("notifications", "all"),
        "current_email_notifications": request.session.get(
            "email_notifications", "true"
        ),
    }

    return render(request, "dashboard/student/home/settings.html", context)


# @login_required
# @teacher_required
# def teacher_dashboard(request, username=None):
#     # Si aucun username n'est fourni, utiliser celui de l'utilisateur connecté
#     if username is None:
#         username = request.user.username

#     try:
#         # Vérifier si l'utilisateur demandé existe et est un enseignant
#         requested_user = get_object_or_404(CustomUser, username=username, role='teacher')
#         teacher = get_object_or_404(Teacher, user=requested_user)
#         profile = get_object_or_404(Profile, user=requested_user)
#         today = timezone.now().date()

#         # Statistiques générales
#         languages = Language.objects.filter(teachers=teacher)
#         total_languages = languages.count()
#         total_students = Student.objects.filter(language__in=languages).distinct().count()
#         total_assignments = Assignment.objects.filter(language__in=languages).count()

#         # Emploi du temps du jour
#         today_schedule = Schedule.objects.filter(
#             teacher=teacher,
#             day=today.strftime('%A')
#         ).order_by('start_time')

#         # Devoirs récents
#         recent_assignments = Assignment.objects.filter(
#             language__in=languages
#         ).order_by('-created_at')[:5]

#         # Statistiques de présence
#         attendance_stats = Attendance.objects.filter(
#             language__in=languages,
#             date=today
#         ).values('status').annotate(count=Count('id'))

#         # Notes récentes
#         recent_marks = Mark.objects.filter(
#             language__in=languages
#         ).order_by('-id')[:5]

#         # Ressources récentes
#         recent_resources = Resource.objects.filter(
#             teachers=requested_user
#         ).order_by('-created_at')[:5]

#         context = {
#             'profile': profile,
#             'user': request.user,
#             'username': username,
#             'teacher': teacher,
#             'total_languages': total_languages,
#             'total_students': total_students,
#             'total_assignments': total_assignments,
#             'today_schedule': today_schedule,
#             'recent_assignments': recent_assignments,
#             'attendance_stats': attendance_stats,
#             'recent_marks': recent_marks,
#             'recent_resources': recent_resources,
#             'languages': languages,
#             'segment': 'index'
#         }

#         return render(request, 'dashboard/teacher/home/index.html', context)

#     except Http404:
#         messages.error(request, "Cet utilisateur n'existe pas ou n'est pas un enseignant.")
#         return redirect('dashboard_home')


def teacher_courses(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    languages = Language.objects.filter(teachers=teacher)

    context = {
        "profile": profile,
        "languages": languages,
        "teacher": teacher,
        "user": user,
        "username": user.username,
        "segment": "courses",
    }
    return render(request, "dashboard/teacher/home/courses.html", context)




def teacher_assignments(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    languages = Language.objects.filter(teachers=teacher)
    assignments = Assignment.objects.filter(language__in=languages)

    if request.method == "POST":
        data = json.loads(request.body)
        assignment = Assignment.objects.create(
            title=data["title"],
            description=data["description"],
            language_id=data["language"],
            type=data["type"],
            due_date=data["due_date"],
        )
        return JsonResponse({"status": "success", "id": assignment.id})

    context = {
        "profile": profile,
        "teacher": teacher,
        "user": user,
        "username": user.username,
        "assignments": assignments,
        "languages": languages,
        "segment": "assignments",
    }
    return render(request, "dashboard/teacher/home/assignments.html", context)


@login_required
def teacher_students(request):

    # Vérification que l'utilisateur est un enseignant
    if request.user.role != "teacher":
        messages.error(request, "Accès réservé aux enseignants.")
        return redirect("dashboard_home")

    # Récupération de l'enseignant connecté
    teacher = get_object_or_404(Teacher, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)

    # Récupération des étudiants de l'enseignant (requête de base)
    students = (
        Student.objects.filter(current_teachers=teacher)
        .select_related("user", "user__user_profile")
        .prefetch_related("languages")
        .order_by("user__last_name", "user__first_name")
    )

    # Récupération des paramètres de filtrage depuis GET
    langue_id = request.GET.get("langue")
    etudiant_id = request.GET.get("etudiant")
    search_query = request.GET.get("recherche", "")

    # Application des filtres
    if langue_id:
        students = students.filter(languages__id=langue_id).distinct()

    if etudiant_id:
        students = students.filter(id=etudiant_id)

    if search_query:
        students = students.filter(
            Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(matricule__icontains=search_query)
            | Q(user__user_profile__city__icontains=search_query)
            | Q(user__user_profile__country__icontains=search_query)
        ).distinct()

    # Pagination
    page = request.GET.get("page", 1)
    paginator = Paginator(students, 5)  # 5 students per page

    try:
        students_page = paginator.page(page)
    except PageNotAnInteger:
        students_page = paginator.page(1)
    except EmptyPage:
        students_page = paginator.page(paginator.num_pages)

    # Données pour les filtres (selects)
    langues = teacher.languages.all().order_by("name")
    all_students_for_select = (
        Student.objects.filter(current_teachers=teacher)
        .select_related("user")
        .order_by("user__last_name")
    )

    # Statistiques
    total_students = students.count()
    filtered_count = students_page.paginator.count

    # Préparation du contexte
    context = {
        # Informations utilisateur
        "profile": profile,
        "teacher": teacher,
        "user": request.user,
        "username": request.user.username,
        # Données principales
        "students": students_page,  # Étudiants paginés
        "all_students": all_students_for_select,  # Pour le select
        "langues": langues,  # Pour le select langues
        # Filtres actifs
        "selected_langue": langue_id,
        "selected_etudiant": etudiant_id,
        "search_query": search_query,
        # Statistiques
        "total_students": total_students,
        "filtered_count": filtered_count,
        "segment": "students",
        # Pour la pagination
        "current_page": page,
        "total_pages": paginator.num_pages,
    }

    return render(request, "dashboard/teacher/home/students.html", context)


@login_required
def teacher_student_detail(request, student_id):

    if request.user.role != "teacher":
        messages.error(request, "Accès réservé aux enseignants.")
        return redirect("dashboard_home")

    teacher = get_object_or_404(Teacher, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)

    # Vérifie que l'étudiant appartient bien à cet enseignant
    student = get_object_or_404(
        Student.objects.filter(current_teachers=teacher), id=student_id
    )

    # Récupération des données associées
    recent_sessions = Session.objects.filter(student=student).order_by(
        "-date", "-start_time"
    )[:10]

    # Statistiques
    total_sessions = Session.objects.filter(student=student).count()
    completed_sessions = Session.objects.filter(
        student=student, status="completed"
    ).count()

 

    context = {
        "profile": profile,
        "teacher": teacher,
        "user": request.user,
        "student": student,
        "recent_sessions": recent_sessions,
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "segment": "students",
    }

    return render(request, "dashboard/teacher/home/student_details.html", context)


@login_required
def student_statistics(request, student_id):
    """
    Statistiques d'un étudiant
    """
    if request.user.role != "teacher":
        messages.error(request, "Accès réservé aux enseignants.")
        return redirect("dashboard_home")

    teacher = get_object_or_404(Teacher, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)

    # Vérifie que l'étudiant appartient bien à cet enseignant
    student = get_object_or_404(
        Student.objects.filter(current_teachers=teacher), id=student_id
    )

    # Calcul des statistiques
    sessions_by_month = {}
    #  sessions = Session.objects.filter(
    #     student=student,
    #     status='completed'
    # ).values('date__month', 'date__year').annotate(
    #     count=Count('id'),
    #      total_hours=Sum('duration_hours')
    #  ).order_by('date__year', 'date__month')

    context = {
        "profile": profile,
        "teacher": teacher,
        "user": request.user,
        "student": student,
        # 'sessions_by_month': sessions_by_month,
        "segment": "students",
    }

    return render(request, "dashboard/teacher/home/student_statistics.html", context)


@login_required
def export_students_csv(request):
    """
    Export des étudiants au format CSV
    """
    if request.user.role != "teacher":
        messages.error(request, "Accès réservé aux enseignants.")
        return redirect("dashboard_home")

    teacher = get_object_or_404(Teacher, user=request.user)

    # CORRECTION 1 : current_teachers au lieu de current_teacher
    students = Student.objects.filter(current_teachers=teacher)

    # Application des mêmes filtres que la vue principale
    langue_id = request.GET.get("langue")
    search_query = request.GET.get("recherche", "")

    if langue_id:
        students = students.filter(languages__id=langue_id).distinct()

    if search_query:
        students = students.filter(
            Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(matricule__icontains=search_query)  # Ajouté pour cohérence
        ).distinct()

    # Préparation de la réponse CSV
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="etudiants_{teacher.user.username}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    )
    response.write("\ufeff".encode("utf8"))  # BOM pour Excel UTF-8

    writer = csv.writer(response, delimiter=";")

    # En-têtes
    writer.writerow(
        [
            "ID",
            "Matricule",
            "Nom",
            "Prénom",
            "Email",
            "Téléphone",
            "Langues",
            "Ville",
            "Pays",
            "Adresse",
            "Date d'inscription",
            "Heures achetées",
            "Heures utilisées",
            "Heures restantes",
            "Enseignants actuels",  # Changé au pluriel
        ]
    )

    # Optimisation : Chargement anticipé des relations
    students = students.select_related(
        'user',
        'user__user_profile'  # CORRECTION 2 : user__user_profile
    ).prefetch_related(
        'languages',
        'current_teachers'
    )

    # Données
    for student in students:
        # Récupération des langues
        langues = ", ".join([lang.name for lang in student.languages.all()])
        
        # CORRECTION 3 : Gestion de current_teachers (ManyToMany)
        current_teachers = ", ".join([
            teacher.user.get_full_name() 
            for teacher in student.current_teachers.all()
        ]) if student.current_teachers.exists() else "Non assigné"
        
        # Récupération du profil (CORRECTION 2)
        profile = student.user.user_profile if hasattr(student.user, 'user_profile') else None
        
        writer.writerow(
            [
                student.id,
                student.matricule,
                student.user.last_name or "",
                student.user.first_name or "",
                student.user.email or "",
                profile.number if profile else "",      # CORRECTION 2
                langues,
                profile.city if profile else "",        # CORRECTION 2
                profile.country if profile else "",     # CORRECTION 2
                profile.address if profile else "",     # CORRECTION 2
                student.date_joined.strftime("%d/%m/%Y") if student.date_joined else "",
                student.total_hours_purchased,
                student.total_hours_used,
                student.hours_remaining,
                current_teachers,  # CORRECTION 3
            ]
        )

    return response



def teacher_languages(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    languages = Language.objects.filter(teachers=teacher)

    # Récupérer les étudiants qui ont cet enseignant comme current_teacher
    students = Student.objects.filter(current_teacher=teacher).distinct()

    context = {
        "profile": profile,
        "teacher": teacher,
        "user": user,
        "username": user.username,
        "languages": languages,
        "students": students,
        "segment": "languages",
    }
    return render(request, "dashboard/teacher/home/languages.html", context)


# API endpoints pour les actions AJAX


def api_filter_students(request):
    user = request.user
    teacher = get_object_or_404(Teacher, user=user)
    search = request.GET.get("search")

    students = Student.objects.filter(current_teacher=teacher).distinct()

    if search:
        students = students.filter(
            Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__email__icontains=search)
        )

    data = [
        {
            "id": student.id,
            "full_name": student.user.get_full_name(),
            "email": student.user.email,
            "languages": [lang.name for lang in student.languages.all()],
            "matricule": student.matricule,
        }
        for student in students
    ]

    return JsonResponse(data, safe=False)


def api_filter_assignments(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    languages = Language.objects.filter(teachers=teacher)
    type_filter = request.GET.get("type")
    language_id = request.GET.get("language")
    status = request.GET.get("status")

    assignments = Assignment.objects.filter(language__in=languages)

    if type_filter:
        assignments = assignments.filter(type=type_filter)
    if language_id:
        assignments = assignments.filter(language_id=language_id)
    if status:
        assignments = assignments.filter(status=status)

    data = [
        {
            "profile": profile,
            "teacher": teacher,
            "user": user,
            "username": user.username,
            "id": assignment.id,
            "title": assignment.title,
            "description": assignment.description,
            "type": assignment.type,
            "status": assignment.status,
            "due_date": assignment.due_date.strftime("%d/%m/%Y"),
            "submissions_count": assignment.submissions.count(),
        }
        for assignment in assignments
    ]

    return JsonResponse(data, safe=False)


# Nouvelles vues pour le cahier des charges


@login_required
def session_detail_view(request, session_id):
    """Vue détaillée d'une séance avec possibilité de feedback"""
    session = get_object_or_404(Session, id=session_id)
    # Vérifier que l'utilisateur a accès à cette séance
    if request.user.role == "student" and session.student.user != request.user:
        raise Http404("Accès non autorisé")
    elif request.user.role == "teacher" and session.teacher.user != request.user:
        raise Http404("Accès non autorisé")

    if request.method == "POST":
        feedback = request.POST.get("feedback")
        if feedback and request.user.role == "teacher":
            session.feedback = feedback
            session.save()
            messages.success(request, "Feedback enregistré avec succès")
            return redirect("session_detail", session_id=session_id)

    context = {
        "session": session,
        "user": request.user,
    }

    # Choisir le bon template selon le rôle
    if request.user.role == "student":
        return render(request, "dashboard/student/home/session_detail.html", context)
    else:
        return render(request, "dashboard/teacher/home/session_detail.html", context)


@login_required
def session_status_update(request, session_id):
    """API pour mettre à jour le statut d'une séance"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Méthode non autorisée"})

    if request.user.role != "teacher":
        return JsonResponse({"success": False, "error": "Accès non autorisé"})

    try:
        session = get_object_or_404(Session, id=session_id, teacher__user=request.user)
        new_status = request.POST.get("status")

        if new_status in dict(Session.STATUS_CHOICES):
            session.status = new_status
            session.save()

            # Créer une notification pour l'étudiant
            Notification.objects.create(
                user=session.student.user,
                notification_type="session_reminder",
                title=f"Statut de séance mis à jour",
                message=f"Votre séance de {session.language.name} du {session.date} est maintenant {session.get_status_display()}",
            )

            return JsonResponse(
                {"success": True, "message": "Statut mis à jour avec succès"}
            )
        else:
            return JsonResponse({"success": False, "error": "Statut invalide"})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def teacher_evaluations_add(request):
    """Vue pour ajouter une nouvelle évaluation"""
    if request.user.role != "teacher":
        raise Http404("Cette page est réservée aux enseignants")

    teacher = get_object_or_404(Teacher, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == "POST":
        try:
            student_id = request.POST.get("student")
            language_id = request.POST.get("language")
            evaluation_type = request.POST.get("evaluation_type")
            score = request.POST.get("score")
            comments = request.POST.get("comments")

            student = get_object_or_404(Student, id=student_id)
            language = get_object_or_404(Language, id=language_id)

            Evaluation.objects.create(
                student=student,
                teacher=teacher,
                language=language,
                evaluation_type=evaluation_type,
                score=score,
                comments=comments,
            )

            messages.success(request, "Évaluation ajoutée avec succès")
            return redirect("teacher_evaluations")

        except Exception as e:
            messages.error(request, f"Erreur lors de l'ajout: {str(e)}")

    students = Student.objects.filter(current_teacher=teacher)
    languages = teacher.languages.all()
    evaluation_types = Evaluation.EVALUATION_TYPES

    context = {
        "students": students,
        "languages": languages,
        "evaluation_types": evaluation_types,
        "teacher": teacher,
        "profile": profile,
        "user": request.user,
    }

    return render(request, "dashboard/teacher/home/evaluations_add.html", context)


@login_required
def evaluation_edit(request, evaluation_id):
    """Vue pour éditer une évaluation existante"""
    if request.user.role != "teacher":
        raise Http404("Cette page est réservée aux enseignants")

    evaluation = get_object_or_404(
        Evaluation, id=evaluation_id, teacher__user=request.user
    )

    if request.method == "POST":
        try:
            evaluation.score = request.POST.get("score")
            evaluation.comments = request.POST.get("comments", "")
            evaluation.save()

            messages.success(request, "Évaluation modifiée avec succès")
            return redirect("evaluations_view")

        except Exception as e:
            messages.error(request, f"Erreur lors de la modification: {str(e)}")

    context = {
        "evaluation": evaluation,
        "teacher": evaluation.teacher,
        "profile": get_object_or_404(Profile, user=request.user),
        "user": request.user,
    }

    return render(request, "dashboard/teacher/home/evaluation_edit.html", context)



@login_required
def teacher_resources_add_student(request):
    """Vue pour ajouter des ressources pour un étudiant spécifique"""
    if request.user.role != "teacher":
        raise Http404("Cette page est réservée aux enseignants")

    teacher = get_object_or_404(Teacher, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == "POST":
        try:
            title = request.POST.get("title")
            description = request.POST.get("description")
            resource_type = request.POST.get("resource_type")
            student_id = request.POST.get("student")
            language_id = request.POST.get("language")

            # Gérer le fichier ou l'URL
            file = request.FILES.get("file")
            url = request.POST.get("url")

            student = get_object_or_404(Student, id=student_id)
            language = get_object_or_404(Language, id=language_id)
            language = get_object_or_404(Language, id=language_id) if language_id else None

            resource = Resource.objects.create(
                title=title,
                description=description,
                resource_type=resource_type,
                file=file,
                url=url,
                teachers=request.user,
            )

            # Ajouter les relations
            resource.languages.add(language)
            if language:
                resource.languages.add(language)

            # Créer une notification pour l'étudiant
            Notification.objects.create(
                user=student.user,
                notification_type="system",
                title="Nouvelle ressource disponible",
                message=f"Votre enseignant a ajouté une nouvelle ressource: {title}",
            )

            messages.success(request, "Ressource ajoutée avec succès")
            return redirect("teacher_resources")

        except Exception as e:
            messages.error(request, f"Erreur lors de l'ajout: {str(e)}")

    students = Student.objects.filter(current_teacher=teacher)
    languages = teacher.languages.all()
    languages = Language.objects.filter(teachers=teacher)
    resource_types = Resource.RESOURCE_TYPES

    context = {
        "students": students,
        "languages": languages,
        "languages": languages,
        "resource_types": resource_types,
        "teacher": teacher,
        "profile": profile,
        "user": request.user,
    }

    return render(request, "dashboard/teacher/home/resources_add_student.html", context)


@login_required
def certificates_view(request):
    """Vue des certificats pour les étudiants"""
    if request.user.role != "student":
        raise Http404("Cette page est réservée aux étudiants")

    student = get_object_or_404(Student, user=request.user)
    certificates = Certificate.objects.filter(student=student, is_active=True)
    profile = get_object_or_404(Profile, user=request.user)

    context = {"certificates": certificates, "user": request.user, "profile": profile}
    return render(request, "dashboard/student/home/certificates.html", context)


@login_required
def evaluations_view(request):
    if request.user.role == "student":
        student = get_object_or_404(Student, user=request.user)
        profile = get_object_or_404(Profile, user=request.user)
        evaluations = Evaluation.objects.filter(student=student)
        return render(
            request,
            "dashboard/student/home/evaluations.html",
            {"evaluations": evaluations, "user": request.user, "profile": profile},
        )
    elif request.user.role == "teacher":
        teacher = get_object_or_404(Teacher, user=request.user)
        evaluations = Evaluation.objects.filter(teacher=teacher)
        profile = get_object_or_404(Profile, user=request.user)
        return render(
            request,
            "dashboard/teacher/home/evaluations.html",
            {
                "evaluations": evaluations,
                "teacher": teacher,
                "user": request.user,
                "profile": profile,
            },
        )
    else:
        raise Http404("Accès non autorisé")


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by(
        "-created_at"
    )
    profile = get_object_or_404(Profile, user=request.user)
    notification_id = request.POST.get("notification_id")

    # check if notification_id is provided to mark as read
    if notification_id:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({"success": True})

    context = {"notifications": notifications, "user": request.user, "profile": profile}

    # Choisir le bon template selon le rôle
    if request.user.role == "student":
        return render(request, "dashboard/student/home/notifications.html", context)
    else:
        return render(request, "dashboard/teacher/home/notifications.html", context)


@login_required
def notifications_mark_all_read(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Méthode non autorisée"})


@login_required
def delete_notification(request):
    notification_id = request.POST.get("notification_id")

    # check if notification_id is provided to mark as read
    if notification_id:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "ID de notification manquant"})


@login_required
def payments_view(request):
    """Vue des paiements pour les étudiants"""
    if request.user.role != "student":
        raise Http404("Cette page est réservée aux étudiants")

    student = get_object_or_404(Student, user=request.user)
    payments = Payment.objects.filter(student=student)
    total_paid = (
        payments.filter(status="paid").aggregate(total=Sum("amount"))["total"] or 0
    )
    profile = get_object_or_404(Profile, user=request.user)
    user = request.user

    context = {
        "payments": payments,
        "student": student,
        "user": user,
        "profile": profile,
        "total_paid": total_paid,
    }
    return render(request, "dashboard/student/home/payments.html", context)



@login_required
def teacher_sessions_view(request):
   
    if request.user.role != "teacher":
        raise Http404("Cette page est réservée aux enseignants")

    teacher = get_object_or_404(Teacher, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)
    availables_students = Student.objects.filter(current_teachers=teacher)
    # Filtres
    language_filter = request.GET.get("language")
    status_filter = request.GET.get("status")
    date_filter = request.GET.get("date")

    sessions = Session.objects.filter(teacher=teacher)

    if language_filter:
        sessions = sessions.filter(language__code=language_filter)
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    if date_filter:
        sessions = sessions.filter(date=date_filter)

    sessions = sessions.order_by("date", "start_time")
    scheduled_count = sessions.filter(status='scheduled').count()
    completed_count = sessions.filter(status='completed').count()
    rescheduled_count = sessions.filter(status='rescheduled').count()
    # formular management
    if request.method == "POST":
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.teacher = teacher
            session.save()
            form.save_m2m()
            messages.success(request, "La session a été créée avec succès !")
            return redirect("teacher_sessions")
    else:
        form = SessionForm()

    context = {
        "scheduled_count": scheduled_count,
        "completed_count": completed_count,
        "rescheduled_count": rescheduled_count,
        "form": form,
        "sessions": sessions,
        "teacher": teacher,
        "languages": teacher.languages.all(),
        "status_choices": Session.STATUS_CHOICES,
        "profile": profile,
        "filters": {
            "language": language_filter,
            "status": status_filter,
            "date": date_filter,
        },
        "user": request.user,
        "availables_students": availables_students
    }
    return render(request, "dashboard/teacher/home/sessions.html", context)


@login_required
def get_student_session_by_id(request, session_id):
    teacher = get_object_or_404(Teacher, user=request.user)
    student = Student.objects.filter(id=session_id, current_teachers=teacher).first()
    sessions = Session.objects.filter(student__id=session_id, teacher=teacher).order_by("date", "start_time")
     
    context ={
        "sessions": sessions,
        "student": student   
    }
    
    return render(  request, "dashboard/teacher/home/sessions.html", context  )

@login_required
def delete_student_session_by_id(request, session_id):
    teacher = get_object_or_404(Teacher, user=request.user)
    session = get_object_or_404(Session, id=session_id, teacher=teacher)
    session.delete()
    messages.success(request, "La session a été supprimée avec succès !")
    return redirect("teacher_sessions")




@login_required
def student_sessions_view(request):

    if request.user.role != "student":
        raise Http404("Cette page est réservée aux étudiants")

    student = get_object_or_404(Student, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)
    # Filtres
    status_filter = request.GET.get("status")
    date_filter = request.GET.get("date")

    sessions = Session.objects.filter(student=student)

    if status_filter:
        sessions = sessions.filter(status=status_filter)
    if date_filter:
        sessions = sessions.filter(date=date_filter)

    sessions = sessions.order_by("date", "start_time")

    context = {
        "sessions": sessions,
        "student": student,
        "status_choices": Session.STATUS_CHOICES,
        "profile": profile,
        "filters": {
            "status": status_filter,
            "date": date_filter,
        },
        "user": request.user,
    }
    return render(request, "dashboard/student/home/sessions.html", context)


def test_template_tags(request):
    """Vue de test pour vérifier que les template tags fonctionnent"""
    return render(request, "dashboard/teacher/home/test_template_tags.html", {})




##Schedule views

#for student
@login_required
def schedule_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    context = {
        "profile": profile,
        "user": user,
        "username": user.username
    }

    if user.role == "student":
        student = get_object_or_404(Student, user=user)
        # Récupérer les schedules liés aux compétences de l'étudiant
        schedule = Schedule.objects.filter(student=student ).order_by(
            "day", "start_time"
        )
        context["schedule"] = schedule
        return render(request, "dashboard/student/home/schedule.html", context)
    else:
        return render(request, "404.html", context)




#for teacher
@login_required
def teacher_schedule_view(request):
    """Vue principale de l'emploi du temps"""
    if request.user.role != "teacher":
        messages.error(request, "Accès réservé aux enseignants.")
        return redirect('dashboard')
    
    teacher = get_object_or_404(Teacher, user=request.user)
    
    # Calcul de la semaine actuelle
    today = date.today()
    week_number = int(request.GET.get('week', 0))
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_number)
    week_end = week_start + timedelta(days=6)
    
    # Jours de la semaine
    week_days = []
    for i in range(7):  # Lundi à Dimanche
        day_date = week_start + timedelta(days=i)
        week_days.append({
            'name': Schedule.DAY_CHOICES[i][0],
            'date': day_date,
            'is_today': day_date == today,
            'column': i + 2
        })
    
   
    hours = []
    for hour in range(0, 24):  #
        hours.append({
            'value': f"{hour:02d}:00",
            'display': f"{hour:02d}:00",
            'grid_row': hour - 7  # Commence à 1 pour 8h
        })
    
    # Récupérer les emplois du temps 
    schedules = Schedule.objects.filter(
        teacher=teacher,
        is_active=True
    ).select_related('language', 'student', 'student__user')
    
    # Préparer les données pour le template
    processed_schedules = []
    for schedule in schedules:
        # Calculer la position dans la grille
        start_hour = schedule.start_time.hour
        start_minute = schedule.start_time.minute
        end_hour = schedule.end_time.hour
        end_minute = schedule.end_time.minute
        
        # Calcul des positions en pixels (chaque heure = 60px)
        # Position top: (heure - 8) * 60 + minutes
        top_position = ((start_hour) * 60) + start_minute
        height_position = ((end_hour - start_hour) * 60) + (end_minute - start_minute)
        
        # Ajustements pour les limites
        if top_position < 0:
            height_position += top_position
            top_position = 0
        
        # Limite maximum (8h-20h = 12h * 60px = 720px)
        max_position = 720
        if top_position + height_position > max_position:
            height_position = max_position - top_position
        
        # Trouver la colonne du jour
        day_column = next((day['column'] for day in week_days if day['name'] == schedule.day), 2)
        
        # Couleur unique pour chaque langue
        language_colors = {
            'Anglais': '#4285f4',
            'Français': '#ea4335',
            
        }
        
        color = language_colors.get(schedule.language.name, '#008080')
        
        processed_schedules.append({
            'id': schedule.id,
            'language': schedule.language,
            'student': schedule.student,
            'start_time': schedule.start_time,
            'end_time': schedule.end_time,
            'day': schedule.day,
            'classroom': schedule.classroom,
            'is_active': schedule.is_active,
            'top_position': top_position,
            'height_position': height_position,
            'day_column': day_column,
            'language_color': color,
            'duration_hours': f"{(end_hour - start_hour) + (end_minute - start_minute)/60:.1f}",
        })
    
    # Statistiques
    total_courses = Schedule.objects.filter(teacher=teacher).count()
    today_courses = Schedule.objects.filter(
        teacher=teacher,
        day=today.strftime('%A'),
        is_active=True
    ).count()
    
    # Cours de cette semaine
    this_week_courses = Schedule.objects.filter(
        teacher=teacher,
        is_active=True,
        day__in=[day['name'] for day in week_days]
    ).count()
    
    # Prochains cours (pour sidebar)
    upcoming_courses = Schedule.objects.filter(
        teacher=teacher,
        is_active=True,
        day__in=[day['name'] for day in week_days]
    ).order_by('day', 'start_time')[:5]
    
    context = {
        'teacher': teacher,
        'today': today,
        'current_week_number': week_number,
        'week_start': week_start,
        'week_end': week_end,
        'week_days': week_days,
        'hours': hours,
        'schedules': processed_schedules,
        'total_courses': total_courses,
        'today_courses': today_courses,
        'this_week_courses': this_week_courses,
        'upcoming_courses': upcoming_courses,
        'languages': teacher.languages.all(),
        'languages_count': teacher.languages.count(),
        'students': Student.objects.filter(current_teachers=teacher).select_related('user'),
        'day_choices': Schedule.DAY_CHOICES,
        'grid_start_hour': 8,
        'grid_end_hour': 20,
    }
    
    return render(request, 'dashboard/teacher/home/schedule.html', context)


@login_required
def add_schedule(request):
   
    if request.user.role != "teacher":
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    if request.method == 'POST':
        try:
            teacher = get_object_or_404(Teacher, user=request.user)
            
            schedule = Schedule.objects.create(
                teacher=teacher,
                day=request.POST.get('day'),
                language_id=request.POST.get('language'),
                student_id=request.POST.get('student') or None,
                classroom=request.POST.get('classroom', ''),
                start_time=request.POST.get('start_time'),
                end_time=request.POST.get('end_time'),
                is_active=request.POST.get('is_active', 'true') == 'true'
            )
            
            messages.success(request, 'Cours ajouté avec succès!')
            return JsonResponse({'success': True, 'schedule_id': schedule.id})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})



#edit view schedule after creating
@login_required
def edit_schedule(request, schedule_id):
    if request.user.role != "teacher":
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    teacher = get_object_or_404(Teacher, user=request.user)
    schedule = get_object_or_404(Schedule, id=schedule_id, teacher=teacher)
    
    if request.method == 'POST':
        try:
            schedule.day = request.POST.get('day', schedule.day)
            schedule.language_id = request.POST.get('language', schedule.language_id)
            schedule.student_id = request.POST.get('student') or None
            schedule.classroom = request.POST.get('classroom', schedule.classroom)
            schedule.start_time = request.POST.get('start_time', schedule.start_time)
            schedule.end_time = request.POST.get('end_time', schedule.end_time)
            schedule.is_active = request.POST.get('is_active', 'true') == 'true'
            schedule.save()
            
            messages.success(request, 'Cours modifié avec succès!')
            return JsonResponse({
                'success': True,
                'message': 'Cours modifié avec succès!',
                'schedule_id': schedule.id
                                 })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # Pour GET, retourner les données du cours
    return JsonResponse({
        'success': True,
        'schedule': {
            'id': schedule.id,
            'day': schedule.day,
            'language_id': schedule.language_id,
            'student_id': schedule.student_id,
            'classroom': schedule.classroom,
            'start_time': schedule.start_time.strftime('%H:%M'),
            'end_time': schedule.end_time.strftime('%H:%M'),
            'is_active': schedule.is_active,
        }
    })

@login_required
def delete_schedule(request, schedule_id):
    
    if request.user.role != "teacher":
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    teacher = get_object_or_404(Teacher, user=request.user)
    schedule = get_object_or_404(Schedule, id=schedule_id, teacher=teacher)
    
    if request.method == 'POST':
        try:
            schedule.delete()
            messages.success(request, 'Cours supprimé avec succès!')
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@login_required
def load_schedule_week(request):
    """Charger une semaine spécifique via AJAX"""
    if request.user.role != "teacher":
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    teacher = get_object_or_404(Teacher, user=request.user)
    week_number = int(request.GET.get('week', 0))
    
    # Calcul de la semaine
    today = date.today()
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_number)
    week_end = week_start + timedelta(days=6)
    
    # Jours de la semaine
    week_days = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        week_days.append({
            'name': Schedule.DAY_CHOICES[i][0],
            'date': day_date,
            'is_today': day_date == today,
            'column': i + 2
        })
    
    # Heures (8h à 20h)
    hours = []
    for hour in range(8, 21):
        hours.append({
            'value': f"{hour:02d}:00",
            'display': f"{hour:02d}:00",
            'grid_row': hour - 7
        })
    
    # Récupérer les emplois du temps de cette semaine
    schedules = Schedule.objects.filter(
        teacher=teacher,
        is_active=True,
        day__in=[day['name'] for day in week_days]
    ).select_related('language', 'student', 'student__user')
    
    # Préparer les données
    processed_schedules = []
    for schedule in schedules:
        start_hour = schedule.start_time.hour
        start_minute = schedule.start_time.minute
        end_hour = schedule.end_time.hour
        end_minute = schedule.end_time.minute
        
        # Calcul des positions en pixels
        top_position = ((start_hour - 8) * 60) + start_minute
        height_position = ((end_hour - start_hour) * 60) + (end_minute - start_minute)
        
        # Ajustements pour les limites
        if top_position < 0:
            height_position += top_position
            top_position = 0
        
        max_position = 720
        if top_position + height_position > max_position:
            height_position = max_position - top_position
        
        # Couleurs
        language_colors = {
            'Anglais': '#4285f4',
            'Français': '#ea4335',
            'Espagnol': '#fbbc04',
            'Allemand': '#34a853',
            'Chinois': '#673ab7',
            'Arabe': '#ff6d00',
        }
        
        color = language_colors.get(schedule.language.name, '#4285f4')
        
        processed_schedules.append({
            'id': schedule.id,
            'language': schedule.language,
            'student': schedule.student,
            'start_time': schedule.start_time,
            'end_time': schedule.end_time,
            'day': schedule.day,
            'classroom': schedule.classroom,
            'is_active': schedule.is_active,
            'top_position': top_position,
            'height_position': height_position,
            'language_color': color,
            'duration_hours': f"{(end_hour - start_hour) + (end_minute - start_minute)/60:.1f}",
        })
    
    # Générer le HTML
    context = {
        'week_days': week_days,
        'hours': hours,
        'schedules': processed_schedules,
        'grid_start_hour': 8,
        'grid_end_hour': 20,
    }
    
    # Rendre seulement la partie du calendrier
    rendered_html = render_to_string('dashboard/teacher/home/schedule.html', context)
    
    return JsonResponse({
        'success': True,
        'week_number': week_number,
        'html': rendered_html,
        'week_start': week_start.strftime('%d %b'),
        'week_end': week_end.strftime('%d %b %Y'),
    })


@login_required
def filter_schedule(request):
    """Filtrer l'emploi du temps"""
    if request.user.role != "teacher":
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    teacher = get_object_or_404(Teacher, user=request.user)
    
    # Construire les filtres
    filters = Q(teacher=teacher, is_active=True)
    
    language_id = request.POST.get('language')
    student_id = request.POST.get('student')
    status = request.POST.get('status')
    
    if language_id:
        filters &= Q(language_id=language_id)
    
    if student_id:
        filters &= Q(student_id=student_id)
    
    if status == 'active':
        filters &= Q(is_active=True)
    elif status == 'inactive':
        filters &= Q(is_active=False)
    
    # Récupérer les emplois du temps filtrés
    schedules = Schedule.objects.filter(filters).select_related(
        'language', 'student', 'student__user'
    )
    
    # Calcul de la semaine actuelle pour le contexte
    today = date.today()
    week_number = 0  # Semaine courante
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Jours de la semaine
    week_days = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        week_days.append({
            'name': Schedule.DAY_CHOICES[i][0],
            'date': day_date,
            'is_today': day_date == today,
            'column': i + 2
        })
    
    # Heures
    hours = []
    for hour in range(8, 21):
        hours.append({
            'value': f"{hour:02d}:00",
            'display': f"{hour:02d}:00",
            'grid_row': hour - 7
        })
    
    # Préparer les données
    processed_schedules = []
    for schedule in schedules:
        start_hour = schedule.start_time.hour
        start_minute = schedule.start_time.minute
        end_hour = schedule.end_time.hour
        end_minute = schedule.end_time.minute
        
        # Calcul des positions
        top_position = ((start_hour - 8) * 60) + start_minute
        height_position = ((end_hour - start_hour) * 60) + (end_minute - start_minute)
        
        # Ajustements
        if top_position < 0:
            height_position += top_position
            top_position = 0
        
        max_position = 720
        if top_position + height_position > max_position:
            height_position = max_position - top_position
        
        # Couleurs
        language_colors = {
            'Anglais': '#4285f4',
            'Français': '#ea4335',
            'Espagnol': '#fbbc04',
            'Allemand': '#34a853',
            'Chinois': '#673ab7',
            'Arabe': '#ff6d00',
        }
        
        color = language_colors.get(schedule.language.name, '#4285f4')
        
        processed_schedules.append({
            'id': schedule.id,
            'language': schedule.language,
            'student': schedule.student,
            'start_time': schedule.start_time,
            'end_time': schedule.end_time,
            'day': schedule.day,
            'classroom': schedule.classroom,
            'is_active': schedule.is_active,
            'top_position': top_position,
            'height_position': height_position,
            'language_color': color,
            'duration_hours': f"{(end_hour - start_hour) + (end_minute - start_minute)/60:.1f}",
        })
    
    # Générer le HTML
    context = {
        'week_days': week_days,
        'hours': hours,
        'schedules': processed_schedules,
        'grid_start_hour': 8,
        'grid_end_hour': 20,
    }
    
    rendered_html = render_to_string('dashboard/teacher/includes/calendar_grid.html', context)
    
    return JsonResponse({
        'success': True,
        'html': rendered_html
    })


@login_required
def quick_add_schedule(request):
 
    if request.user.role != "teacher":
        messages.error(request, "Accès non autorisé.")
        return redirect('teacher_schedule')
    
    if request.method == 'POST':
        try:
            teacher = get_object_or_404(Teacher, user=request.user)
            Schedule.objects.create(
                teacher=teacher,
                day=request.POST['day'],
                language_id=request.POST['language'],
                student_id=request.POST.get('student'),
                start_time=request.POST['start_time'],
                end_time=request.POST['end_time'],
                is_active=True
            )
            
            messages.success(request, "Cours ajouté avec succès!")
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")
    
    return redirect('teacher_schedule')




@admin_required
def admin_dashboard(request):
    # Statistiques principales
    total_teachers = Teacher.objects.count()
    total_students = Student.objects.count()
    total_languages = Language.objects.filter(is_active=True).count()
    
    # Séances
    today = timezone.now().date()
    completed_sessions = Session.objects.filter(status='completed').count()
    scheduled_sessions = Session.objects.filter(status='scheduled').count()
    
    # Calcul du taux de présence
    total_sessions = Session.objects.filter(status__in=['completed', 'absent']).count()
    if total_sessions > 0:
        attendance_rate = round((Session.objects.filter(status='completed').count() / total_sessions) * 100, 1)
    else:
        attendance_rate = 0
    
    # Paiements
    total_revenue = Payment.objects.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
    pending_payments = Payment.objects.filter(status='pending').count()
    
    # Demandes en attente
    pending_requests = Request.objects.filter(status='pending').count()
    
    # Certificats récents (7 derniers jours)
    recent_certificates = Certificate.objects.filter(
        issued_date__gte=today - timedelta(days=7)
    ).order_by('-issued_date')[:5]
    
    # Évaluations récentes
    recent_evaluations = Evaluation.objects.order_by('-evaluation_date')[:5]
    
    # Notifications non lues
    unread_notifications = Notification.objects.filter(is_read=False).order_by('-created_at')[:5]
    
    # Séances à venir (pour montrer l'agenda global)
    upcoming_sessions = Session.objects.filter(
        date__gte=today,
        status='scheduled'
    ).order_by('date', 'start_time')[:10]
    
    # Séances du jour
    today_sessions = Session.objects.filter(
        date=today,
        status='scheduled'
    ).order_by('start_time')
    
    # Nouveaux étudiants (inscrits ce mois-ci)
    this_month_start = today.replace(day=1)
    new_students_this_month = Student.objects.filter(
        date_joined__gte=this_month_start
    ).count()
    
    context = {
        'total_teachers': total_teachers,
        'total_students': total_students,
        'total_languages': total_languages,
        'completed_sessions': completed_sessions,
        'scheduled_sessions': scheduled_sessions,
        'attendance_rate': attendance_rate,
        'total_revenue': total_revenue,
        'pending_payments': pending_payments,
        'pending_requests': pending_requests,
        'recent_certificates': recent_certificates,
        'recent_evaluations': recent_evaluations,
        'unread_notifications': unread_notifications,
        'upcoming_sessions': upcoming_sessions,
        'today_sessions': today_sessions,
        'new_students_this_month': new_students_this_month,
    }
    
    return render(request, 'dashboard/admin/home/index.html', context)



@admin_required
def admin_teacher_view(request):
    # Récupérer tous les enseignants avec leurs statistiques
    teachers = Teacher.objects.select_related('user').prefetch_related(
        'languages', 
        'sessions',
        'current_students'
    ).annotate(
        total_students_count=Count('current_students', distinct=True),
        active_sessions_count=Count('sessions', filter=Q(sessions__status='scheduled')),
        completed_sessions_count=Count('sessions', filter=Q(sessions__status='completed'))
    ).all()
    
    # Pagination
    paginator = Paginator(teachers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        "teachers": page_obj,
        "total_teachers": teachers.count(),
        "page_obj": page_obj,
    }
    return render(request, 'dashboard/admin/home/list_teachers.html', context)

@admin_required
def teacher_detail_view(request, teacher_id):
    # Détails d'un enseignant spécifique avec ses étudiants
    teacher = get_object_or_404(Teacher.objects.select_related('user').prefetch_related(
        'languages',
        'current_students__user',
        'current_students__payments',
        'sessions'
    ), id=teacher_id)
    
    # Statistiques de l'enseignant
    students = teacher.current_students.all().annotate(
        total_payments=Sum('payments__amount'),
        total_hours_remaining=Sum('payments__hours_remaining')
    )
    
    # Sessions récentes
    recent_sessions = Session.objects.filter(teacher=teacher).order_by('-date')[:5]
    
    context = {
        "teacher": teacher,
        "students": students,
        "recent_sessions": recent_sessions,
        "total_students": students.count(),
        "total_hours_taught": Session.objects.filter(teacher=teacher, status='completed').count(),
    }
    return render(request, 'dashboard/admin/home/teacher_detail.html', context)

@admin_required
def admin_student_view(request):
    # Liste de tous les étudiants avec statistiques
    students = Student.objects.select_related('user').prefetch_related(
        'current_teachers__user',
        'payments',
        'sessions'
    ).annotate(
        total_paid_amount=Sum('payments__amount', filter=Q(payments__status='paid')),  # Renommé
        paid_hours_purchased=Sum('payments__hours_purchased', filter=Q(payments__status='paid')),  # Renommé
        active_teachers_count=Count('current_teachers', distinct=True),
        completed_sessions_count=Count('sessions', filter=Q(sessions__status='completed'))
    ).all()
    
    # Filtres
    filter_status = request.GET.get('status', 'all')
    
    if filter_status == 'active':
        # Utilisez le champ existant du modèle ou une logique personnalisée
        students = students.filter(total_hours_purchased__gt=0)  # Champ existant
    elif filter_status == 'inactive':
        students = students.filter(total_hours_purchased=0)  # Champ existant
    
    # Calcul des totaux pour les statistiques
    total_hours_purchased_sum = 0
    total_paid_sum = 0
    
    for student in students:
        total_hours_purchased_sum += student.total_hours_purchased 
        total_paid_sum += student.total_paid_amount or 0  
    
    # Pagination
    paginator = Paginator(students, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        "students": page_obj,
        "total_students": students.count(),
        "total_hours_purchased": total_hours_purchased_sum,
        "total_paid_sum": total_paid_sum,
        "page_obj": page_obj,
    }
    return render(request, 'dashboard/admin/home/list_students.html', context)

@admin_required
def student_detail_view(request, student_id):
    # Détails d'un étudiant spécifique
    student = get_object_or_404(Student.objects.select_related('user').prefetch_related(
        'current_teachers__user',
        'payments',
        'sessions__teacher__user',
        'sessions__language',
        'languages'
    ), id=student_id)
    
    # Statistiques financières
    payments = student.payments.filter(status='paid').order_by('-payment_date')
    total_paid = payments.aggregate(total=Sum('amount'))['total'] or 0
    # Sessions
    upcoming_sessions = Session.objects.filter(
        student=student, 
        status='scheduled',
        date__gte=timezone.now().date()
    ).order_by('date', 'start_time')[:5]
    
    context = {
        "student": student,
        "payments": payments,
        "upcoming_sessions": upcoming_sessions,
        "total_paid": total_paid,
        "teachers": student.current_teachers.all(),
    }
    return render(request, 'dashboard/admin/home/student_detail.html', context)