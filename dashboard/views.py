import csv
from multiprocessing import context
from urllib import request
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import Http404, JsonResponse
from datetime import date, datetime, timedelta
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST, require_GET
from .decorators import teacher_required, admin_required, student_required

from dashboard import models
from dashboard.decorators import admin_required
from dashboard.models import (
    CustomUser,
    Student,
    Teacher,
    Profile,
    Language,
    Resource,
    Request,
    Assignment,
    Submission,
    Session,
    SessionSeries,
    Payment,
    Certificate,
    Evaluation,
    Notification,
    Comment,
    PaiementFormateur,
)
from .forms import ProfileUpdateForm, SessionForm, SessionSeriesTeacherForm, ResourceForm, FichePedagogiqueForm, CertificateForm, PaiementFormateurForm, AssignmentAdminForm
from dashboard.services import generate_series_occurrences as _teacher_generate_series
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
        total_sessions = Session.objects.filter(students=student).count()
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
            students=student, date__gte=today, status="scheduled"
        ).order_by("date", "start_time")
        context["upcoming_sessions"] = upcoming_sessions

        # Historique des séances (faites / reportées)
        completed_sessions = Session.objects.filter(
            students=student, status="completed"
        ).order_by("-date")[:10]
        context["completed_sessions"] = completed_sessions

        rescheduled_sessions = Session.objects.filter(
            students=student, status="rescheduled"
        ).order_by("-date")[:5]
        context["rescheduled_sessions"] = rescheduled_sessions

        # Séances : passées les plus récentes d'abord, futures les plus proches ensuite
        sessions_page_num = request.GET.get('sessions_page', 1)
        base_qs = Session.objects.filter(students=student).select_related('language', 'teacher__user')
        past_sessions = list(base_qs.filter(date__lte=today).order_by('-date', '-start_time'))
        future_sessions = list(base_qs.filter(date__gt=today).order_by('date', 'start_time'))
        all_sessions = past_sessions + future_sessions
        sessions_paginator = Paginator(all_sessions, 8)
        context["recent_sessions"] = sessions_paginator.get_page(sessions_page_num)

        # Séances du jour
        today_sessions = Session.objects.filter(students=student, date=today).order_by(
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
        total_sessions = Session.objects.filter(students=student).count()
        completed_count = Session.objects.filter(
            students=student, status="completed"
        ).count()
        

        context.update(
            {
                "total_sessions": total_sessions,
                "completed_sessions_count": completed_count,
                # Tailwind dashboard variables
                "completed_sessions": completed_count,
                "hours_remaining": student.hours_remaining,
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
        sessions_page_num = request.GET.get('sessions_page', 1)
        recent_completed_sessions_qs = Session.objects.filter(
            teacher=teacher,
            status="completed"
        ).order_by("-date", "-start_time")
        sessions_paginator = Paginator(recent_completed_sessions_qs, 5)
        recent_completed_sessions = sessions_paginator.get_page(sessions_page_num)
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

        # Tailwind dashboard variables
        context['sessions_today_count'] = Session.objects.filter(teacher=teacher, date=today).count()
        context['sessions_week_count'] = Session.objects.filter(
            teacher=teacher, date__gte=today, date__lte=today + timedelta(days=7)
        ).count()
        context['total_students_count'] = teacher.total_students

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
        total_sessions = Session.objects.filter(students=student, status='completed').count()
        avg_rating_val = Comment.objects.filter(
            teacher__in=student.current_teachers.all()
        ).aggregate(avg=Avg('rating'))['avg']
        context.update({
            "student": student,
            "total_sessions": total_sessions,
            "avg_rating": round(avg_rating_val, 1) if avg_rating_val else None,
        })
        return render(request, "dashboard/student/home/profile.html", context)

    elif user.role == "teacher":
        teacher = get_object_or_404(Teacher, user=user)
        now = timezone.now()
        total_sessions = Session.objects.filter(teacher=teacher).count()
        completed_sessions = Session.objects.filter(teacher=teacher, status='completed').count()
        sessions_this_month = Session.objects.filter(
            teacher=teacher,
            date__year=now.year,
            date__month=now.month
        ).count()
        evaluations_given = Evaluation.objects.filter(teacher=teacher).count()
        next_session = Session.objects.filter(
            teacher=teacher, status='scheduled', date__gte=now.date()
        ).order_by('date', 'start_time').first()
        context.update({
            "teacher": teacher,
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "sessions_this_month": sessions_this_month,
            "evaluations_given": evaluations_given,
            "next_session": next_session,
        })
        return render(request, "dashboard/teacher/home/profile.html", context)

    elif user.role == "admin":
        total_students = Student.objects.count()
        total_teachers = Teacher.objects.count()
        total_sessions_count = Session.objects.count()
        revenue = Payment.objects.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
        context.update({
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_sessions": total_sessions_count,
            "revenue": revenue,
        })
        return render(request, "dashboard/admin/home/admin_profile.html", context)
    


@login_required
def profile_edit(request):
    user = get_object_or_404(CustomUser, username=request.user.username)
    profile = get_object_or_404(Profile, user=user)

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            update_fields = []
            if first_name:
                user.first_name = first_name
                update_fields.append('first_name')
            if last_name:
                user.last_name = last_name
                update_fields.append('last_name')
            if update_fields:
                user.save(update_fields=update_fields)
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
        return render(request, "dashboard/admin/home/admin_profile_edit.html", context)


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
        resources = Resource.objects.filter(students = student)
        # Obtenir les langues de l'étudiant
        student_languages = student.languages.all()  # Supposons que Student a un champ languages
        
        now = timezone.now()
        
        
        
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

# views/teacher_resources.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone


@login_required
def teacher_resources_dashboard(request):
    user = request.user
    
    # Vérification du rôle
    if user.role != "teacher":
        messages.error(request, "Accès non autorisé")
        return redirect('dashboard')
    
    teacher = get_object_or_404(Teacher, user=user)
    
    # Récupération des ressources
    resources = Resource.objects.filter(teachers=teacher).order_by('-created_at')
    students = Student.objects.filter(current_teachers=teacher)
    
    # Création des formulaires pour les modals
    create_form = ResourceForm(teacher=teacher)
    
    context = {
        'teacher': teacher,
        'resources': resources,
        'students': students,
        'create_form': create_form,
        'now': timezone.now(),
    }
    
    return render(request, 'dashboard/teacher/home/resources.html', context)


@login_required
def resource_create(request):
    if request.user.role != 'teacher':
        return redirect('dashboard')
    teacher = get_object_or_404(Teacher, user=request.user)
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES, teacher=teacher)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.teachers = teacher
            resource.save()
            form.save_m2m()
            resource.languages.set(teacher.languages.all())
            messages.success(request, "Ressource créée.")
            return redirect('teacher_resources_dashboard')
    else:
        form = ResourceForm(teacher=teacher)
    return render(request, 'dashboard/teacher/home/resource_form.html', {
        'form': form, 'titre': 'Nouvelle ressource',
    })


@login_required
def resource_edit(request, resource_id):
    if request.user.role != 'teacher':
        return redirect('dashboard')
    resource = get_object_or_404(Resource, id=resource_id)
    teacher = get_object_or_404(Teacher, user=request.user)
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES, instance=resource)
        if form.is_valid():
            form.save()
            messages.success(request, "Ressource mise à jour.")
            return redirect('teacher_resources_dashboard')
    else:
        form = ResourceForm(instance=resource, teacher=teacher)
    return render(request, 'dashboard/teacher/home/resource_form.html', {
        'form': form, 'resource': resource, 'titre': f'Modifier — {resource.title}',
    })


@login_required
def resource_delete(request, resource_id):
    """Traitement de la suppression d'une ressource"""
    if request.method != 'POST':
        return redirect('teacher_resources_dashboard')
    
    user = request.user
    if user.role != "teacher":
        messages.error(request, "Accès non autorisé")
        return redirect('dashboard')
    
    teacher = get_object_or_404(Teacher, user=user)
    resource = get_object_or_404(Resource, id=resource_id, teachers=teacher)
    
    resource_title = resource.title
    resource.delete()
    messages.success(request, f"La ressource '{resource_title}' a été supprimée.")
    
    return redirect('teacher_resources_dashboard')



@login_required
@require_GET
def get_resource_details(request, resource_id):

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
       
        'file_url': resource.file.url if resource.file else None,
        'url': resource.url,
        'is_visible': resource.is_visible,
        'valid_until': resource.valid_until.strftime('%Y-%m-%d %H:%M') if resource.valid_until else None,
        'created_at': resource.created_at.strftime('%d/%m/%Y %H:%M'),
        'languages': [{'id': lang.id, 'name': lang.name} for lang in resource.languages.all()],
        'students': [{'id': stu.id, 'name': stu.user.get_full_name()} for stu in resource.students.all()],
    }
    
    return JsonResponse(data)



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

        # Récupérer la demande — autorisé si la demande est envoyée à ce prof
        # OU si l'étudiant fait partie de ses élèves (cohérent avec la liste)
        req = Request.objects.filter(id=request_id).filter(
            Q(teacher=teacher) | Q(student__current_teachers=teacher)
        ).distinct().first()
        if req is None:
            raise Request.DoesNotExist
        
        # Mettre à jour le statut selon l'action
        status_map = {
            'process': 'processing',
            'approve': 'approved',
            'reject': 'rejected',
            'pending': 'pending',
            # direct status values from dropdown
            'processing': 'processing',
            'approved': 'approved',
            'rejected': 'rejected',
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


@login_required
@require_POST
def delete_request(request, request_id):
    req = get_object_or_404(Request, id=request_id)
    user = request.user
    if user.role == 'student':
        if req.student.user != user:
            return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)
    elif user.role == 'teacher':
        teacher = get_object_or_404(Teacher, user=user)
        allowed = (req.teacher_id == teacher.pk) or req.student.current_teachers.filter(pk=teacher.pk).exists()
        if not allowed:
            return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)
    else:
        return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)
    req.delete()
    return JsonResponse({'success': True})


def settings_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)

    if request.method == "POST":
        language = request.POST.get("language", "fr")
        notifications = request.POST.get("notifications", "all")
        email_notifications = request.POST.get("email_notifications", "true")

        request.session["language"] = language
        request.session["notifications"] = notifications
        request.session["email_notifications"] = email_notifications

        return redirect("settings_view")

    context = {
        "profile": profile,
        "user": user,
        "username": user.username,
        "current_language": request.session.get("language", "fr"),
        "current_notifications": request.session.get("notifications", "all"),
        "current_email_notifications": request.session.get("email_notifications", "true"),
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




@teacher_required
def teacher_assignments(request):
    teacher = get_object_or_404(Teacher, user=request.user)
    languages = Language.objects.filter(teachers=teacher)
    assignments = Assignment.objects.filter(language__in=languages).order_by('-created_at')
    return render(request, 'dashboard/teacher/home/assignments.html', {
        'teacher': teacher, 'assignments': assignments, 'languages': languages,
        'segment': 'assignments',
    })


@teacher_required
def teacher_assignment_create(request):
    teacher = get_object_or_404(Teacher, user=request.user)
    if request.method == 'POST':
        form = AssignmentAdminForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Devoir créé.")
            return redirect('teacher_assignments')
    else:
        form = AssignmentAdminForm()
    return render(request, 'dashboard/teacher/home/assignment_form.html', {
        'form': form, 'titre': 'Nouveau devoir',
    })


@teacher_required
def teacher_assignment_edit(request, assign_id):
    assignment = get_object_or_404(Assignment, id=assign_id)
    if request.method == 'POST':
        form = AssignmentAdminForm(request.POST, instance=assignment)
        if form.is_valid():
            form.save()
            messages.success(request, "Devoir mis à jour.")
            return redirect('teacher_assignments')
    else:
        form = AssignmentAdminForm(instance=assignment)
    return render(request, 'dashboard/teacher/home/assignment_form.html', {
        'form': form, 'assignment': assignment,
        'titre': f'Modifier — {assignment.title}',
    })


@teacher_required
def teacher_assignment_delete(request, assign_id):
    assignment = get_object_or_404(Assignment, id=assign_id)
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, "Devoir supprimé.")
        return redirect('teacher_assignments')
    return render(request, 'dashboard/teacher/home/assignment_form.html', {
        'assignment': assignment, 'confirming_delete': True,
        'titre': f'Supprimer — {assignment.title}',
    })


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
    today = timezone.now().date()
    recent_sessions = Session.objects.filter(
        students=student, date__gte=today
    ).order_by('date', 'start_time')[:10]

    # Statistiques
    total_sessions = Session.objects.filter(students=student).count()
    completed_sessions = Session.objects.filter(
        students=student, status="completed"
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
    if request.user.role == "student" and not session.students.filter(user=request.user).exists():
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

            # Créer une notification pour tous les étudiants
            for student in session.students.all():
                Notification.objects.create(
                    user=student.user,
                    notification_type='evaluation_request',
                    title="Votre cours est terminé — donnez votre avis",
                    message=f"Votre séance de {session.language} avec {session.teacher} du {session.date} est terminée. Cliquez pour évaluer.",
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
            return redirect("evaluations_view")

        except Exception as e:
            messages.error(request, f"Erreur lors de l'ajout: {str(e)}")

    students = Student.objects.filter(current_teachers=teacher)
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
def teacher_evaluation_delete(request, evaluation_id):
    if request.user.role != "teacher" or request.method != "POST":
        raise Http404
    evaluation = get_object_or_404(Evaluation, id=evaluation_id, teacher__user=request.user)
    evaluation.delete()
    messages.success(request, "Évaluation supprimée.")
    return redirect("evaluations_view")


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
    """Vue des certificats — redirige selon le rôle."""
    if request.user.role == "admin":
        return redirect("admin_certificates_list")

    if request.user.role == "teacher":
        messages.info(request, "La gestion des certificats est réservée à l'administration.")
        return redirect("teacher_view", username=request.user.username)

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
def teacher_session_create(request):
    if request.user.role != 'teacher':
        raise Http404
    teacher = get_object_or_404(Teacher, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)
    is_recurring = False

    if request.method == 'POST':
        is_recurring = request.POST.get('is_recurring') == 'on'
        if is_recurring:
            series_form = SessionSeriesTeacherForm(request.POST, teacher=teacher)
            if series_form.is_valid():
                series = series_form.save(commit=False)
                series.teacher = teacher
                series.save()
                series_form.save_m2m()
                occurrences = _teacher_generate_series(series)
                messages.success(request, f"Série créée — {len(occurrences)} séances générées.")
                return redirect('teacher_sessions')
            form = SessionForm(teacher=teacher)
        else:
            form = SessionForm(request.POST, teacher=teacher)
            series_form = SessionSeriesTeacherForm(teacher=teacher)
            if form.is_valid():
                session = form.save(commit=False)
                session.teacher = teacher
                session.save()
                form.save_m2m()
                messages.success(request, "Séance créée avec succès.")
                return redirect('teacher_sessions')
    else:
        from datetime import date as _date
        initial = {}
        start = request.GET.get('start', '')
        if start:
            initial['date'] = start[:10]
            initial['start_time'] = start[11:16] if len(start) > 10 else ''
        end = request.GET.get('end', '')
        if end:
            initial['end_time'] = end[11:16] if len(end) > 10 else ''
        form = SessionForm(initial=initial, teacher=teacher)
        series_form = SessionSeriesTeacherForm(teacher=teacher)

    return render(request, 'dashboard/teacher/home/session_form.html', {
        'form': form,
        'series_form': series_form,
        'is_recurring': is_recurring,
        'titre': 'Nouvelle séance',
        'teacher': teacher,
        'profile': profile,
        'user': request.user,
    })


@login_required
def teacher_session_edit(request, session_id):
    if request.user.role != 'teacher':
        raise Http404
    teacher = get_object_or_404(Teacher, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)
    session = get_object_or_404(Session, pk=session_id, teacher=teacher)

    if request.method == 'POST':
        form = SessionForm(request.POST, instance=session, teacher=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, "Séance modifiée avec succès.")
            return redirect('teacher_sessions')
    else:
        form = SessionForm(instance=session, teacher=teacher)

    return render(request, 'dashboard/teacher/home/session_form.html', {
        'form': form,
        'titre': 'Modifier la séance',
        'session': session,
        'teacher': teacher,
        'profile': profile,
        'user': request.user,
    })


@login_required
def teacher_session_status_update(request, session_id):
    if request.user.role != 'teacher' or request.method != 'POST':
        raise Http404
    teacher = get_object_or_404(Teacher, user=request.user)
    session = get_object_or_404(Session, pk=session_id, teacher=teacher)

    new_status = request.POST.get('status')
    valid_statuses = [s[0] for s in Session.STATUS_CHOICES]
    if new_status not in valid_statuses:
        messages.error(request, "Statut invalide.")
        return redirect('teacher_sessions')

    old_status = session.status
    session.status = new_status
    session.save()

    status_labels = {
        'scheduled': 'Planifiée',
        'completed': 'Terminée',
        'cancelled': 'Annulée',
        'rescheduled': 'Reportée',
        'absent': 'Absent',
    }
    label = status_labels.get(new_status, new_status)
    title = f"Statut séance mis à jour : {label}"
    body = (
        f"La séance du {session.date.strftime('%d/%m/%Y')} "
        f"({session.language}) avec {teacher.user.get_full_name()} "
        f"est maintenant marquée « {label} »."
    )

    admin_users = CustomUser.objects.filter(role='admin')
    for admin in admin_users:
        Notification.objects.create(
            user=admin,
            notification_type='system',
            title=title,
            message=body,
        )

    for student in session.students.all():
        Notification.objects.create(
            user=student.user,
            notification_type='system',
            title=title,
            message=body,
        )

    messages.success(request, f"Statut mis à jour : {label}.")
    return redirect('teacher_sessions')


@login_required
def get_student_session_by_id(request, session_id):
    teacher = get_object_or_404(Teacher, user=request.user)
    student = Student.objects.filter(id=session_id, current_teachers=teacher).first()
    sessions = Session.objects.filter(students__id=session_id, teacher=teacher).order_by("date", "start_time")
     
    context ={
        "sessions": sessions,
        "student": student   
    }
    
    return render(  request, "dashboard/teacher/home/sessions.html", context  )



@login_required
def student_sessions_view(request):

    if request.user.role != "student":
        raise Http404("Cette page est réservée aux étudiants")

    student = get_object_or_404(Student, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)
    # Filtres
    status_filter = request.GET.get("status")
    date_filter = request.GET.get("date")

    sessions = Session.objects.filter(students=student)

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




@admin_required
def admin_dashboard(request):
    import json as _json
    from datetime import date as _date
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
    
    # Nouveaux KPIs pédagogiques
    active_students = Student.objects.filter(statuts='actif').count()
    active_teachers = Teacher.objects.filter(statut__in=['actif', 'disponible']).count()
    total_sessions_all = Session.objects.filter(seance_realisee=True).count()
    fiches_completees = Session.objects.filter(fiche_completee=True).count()
    taux_completion_fiches = round((fiches_completees / total_sessions_all * 100), 1) if total_sessions_all > 0 else 0
    total_heures_enseignees = Session.objects.filter(
        seance_realisee=True
    ).aggregate(total=Sum('duree_minutes'))['total'] or 0
    total_heures_enseignees = round(total_heures_enseignees / 60, 1)
    total_paiements_formateurs = PaiementFormateur.objects.filter(
        statut='paye'
    ).aggregate(total=Sum('montant'))['total'] or 0
    sessions_en_attente_validation = Session.objects.filter(
        fiche_completee=True, statut_validation='en_attente'
    ).count()

    # Variables for new Tailwind dashboard
    sessions_today_count = Session.objects.filter(date=today).count()
    revenue_total = Payment.objects.filter(status='paid').aggregate(
        total=Sum('amount'))['total'] or 0
    sessions_page_num = request.GET.get('sessions_page', 1)
    base_qs = Session.objects.select_related('teacher__user', 'language')
    past_sessions = list(base_qs.filter(date__lte=today).order_by('-date', '-start_time'))
    future_sessions = list(base_qs.filter(date__gt=today).order_by('date', 'start_time'))
    sessions_paginator = Paginator(past_sessions + future_sessions, 8)
    recent_sessions = sessions_paginator.get_page(sessions_page_num)

    # ── Graphes : séances sur 6 mois ─────────────────────────────
    labels = []
    completed_data = []
    scheduled_data = []
    revenue_data = []
    new_students_data = []
    for i in range(5, -1, -1):
        ref = today.replace(day=1)
        # rewind i months
        m = ref.month - i
        y = ref.year
        while m <= 0:
            m += 12
            y -= 1
        first_day = _date(y, m, 1)
        # last day of month
        if m == 12:
            last_day = _date(y + 1, 1, 1)
        else:
            last_day = _date(y, m + 1, 1)
        labels.append(first_day.strftime('%b %Y'))
        completed_data.append(
            Session.objects.filter(status='completed', date__gte=first_day, date__lt=last_day).count()
        )
        scheduled_data.append(
            Session.objects.filter(status='scheduled', date__gte=first_day, date__lt=last_day).count()
        )
        rev = Payment.objects.filter(
            status='paid', payment_date__date__gte=first_day, payment_date__date__lt=last_day
        ).aggregate(total=Sum('amount'))['total'] or 0
        revenue_data.append(float(rev))

        ns = Student.objects.filter(
            date_joined__gte=first_day, date_joined__lt=last_day
        ).count()
        new_students_data.append(ns)

    marge_nette = float(revenue_total) - float(total_paiements_formateurs)

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
        # Nouveaux KPIs
        'active_students': active_students,
        'active_teachers': active_teachers,
        'total_sessions_all': total_sessions_all,
        'taux_completion_fiches': taux_completion_fiches,
        'total_heures_enseignees': total_heures_enseignees,
        'total_paiements_formateurs': total_paiements_formateurs,
        'sessions_en_attente_validation': sessions_en_attente_validation,
        # Tailwind dashboard variables
        'sessions_today': sessions_today_count,
        'revenue_total': revenue_total,
        'recent_sessions': recent_sessions,
        # Graphes
        'sessions_labels': _json.dumps(labels),
        'sessions_completed_data': _json.dumps(completed_data),
        'sessions_scheduled_data': _json.dumps(scheduled_data),
        'marge_nette': round(marge_nette, 2),
        'revenue_labels': _json.dumps(labels),
        'revenue_data': _json.dumps(revenue_data),
        'new_students_labels': _json.dumps(labels),
        'new_students_data': _json.dumps(new_students_data),
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
    ).order_by('id')
    
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
        total_paid_amount_by_student=Sum('payments__amount', filter=Q(payments__status='paid')), 
        paid_hours_purchased=Sum('payments__hours_purchased', filter=Q(payments__status='paid')),  # Renommé
        active_teachers_count=Count('current_teachers', distinct=True),
        completed_sessions_count=Count('sessions', filter=Q(sessions__status='completed'))
    ).order_by('id')
   
        
    # Filtres
    filter_status = request.GET.get('status', 'all')
    
    if filter_status == 'active':
        # Utilisez le champ existant du modèle ou une logique personnalisée
        students = students.filter(total_hours_purchased__gt=0)  # Champ existant
    elif filter_status == 'inactive':
        students = students.filter(total_hours_purchased=0)  # Champ existant
    
    # Calcul des totaux pour les statistiques
    total_hours_purchased_sum = 0
    total_paid_sum = Payment.objects.filter(status='paid').aggregate(
        total=Sum('amount'))['total'] or 0
    
    for student in students:
        total_hours_purchased_sum += student.total_hours_purchased 
    
   
    
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
        students=student,
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


# ─────────────────────────────────────────────────────────────
#  FICHE PÉDAGOGIQUE (formateur)
# ─────────────────────────────────────────────────────────────

@login_required
def fiche_pedagogique_edit(request, session_id):
    """Permet au formateur de remplir la fiche pédagogique d'une séance (teacher uniquement)."""
    session = get_object_or_404(Session, id=session_id)

    if request.user.role in ('admin', 'student'):
        raise Http404
    if request.user.role != 'teacher':
        messages.error(request, "Accès refusé.")
        return redirect('dashboard')

    teacher = get_object_or_404(Teacher, user=request.user)
    if session.teacher != teacher:
        messages.error(request, "Vous n'êtes pas autorisé à modifier cette fiche.")
        return redirect('teacher_sessions')

    if request.method == 'POST':
        form = FichePedagogiqueForm(request.POST, instance=session)
        if form.is_valid():
            fiche = form.save(commit=False)
            fiche.fiche_completee = True
            fiche.save()
            messages.success(request, "Fiche pédagogique enregistrée avec succès.")
            return redirect('teacher_sessions')
    else:
        form = FichePedagogiqueForm(instance=session)

    return render(request, 'dashboard/teacher/home/fiche_pedagogique.html', {
        'form': form,
        'session': session,
    })


@login_required
def fiche_pedagogique_detail(request, session_id):
    """Affiche la fiche pédagogique complète d'une séance (lecture seule)."""
    session = get_object_or_404(Session, id=session_id)

    if request.user.role == 'teacher':
        teacher = get_object_or_404(Teacher, user=request.user)
        if session.teacher != teacher:
            raise Http404
    elif request.user.role == 'student':
        student = get_object_or_404(Student, user=request.user)
        if not session.students.filter(id=student.id).exists():
            raise Http404
    else:
        raise Http404

    return render(request, 'dashboard/teacher/home/fiche_pedagogique_detail.html', {
        'session': session,
    })


# ─────────────────────────────────────────────────────────────
#  VALIDATION DES SÉANCES (admin)
# ─────────────────────────────────────────────────────────────

@admin_required
def admin_sessions_list(request):
    """Liste toutes les séances avec filtres de validation."""
    today = timezone.now().date()
    sessions = Session.objects.select_related(
        'teacher__user', 'language'
    ).prefetch_related('students__user').filter(date__gte=today).order_by('date', 'start_time')

    statut = request.GET.get('statut_validation', '')
    teacher_id = request.GET.get('teacher', '')
    if statut:
        sessions = sessions.filter(statut_validation=statut)
    if teacher_id:
        sessions = sessions.filter(teacher_id=teacher_id)

    paginator = Paginator(sessions, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/admin/home/sessions_list.html', {
        'sessions': page_obj,
        'teachers': Teacher.objects.all(),
        'statut_filter': statut,
        'teacher_filter': teacher_id,
    })


@admin_required
def admin_valider_session(request, session_id):
    """Valide ou refuse une fiche pédagogique (admin)."""
    session = get_object_or_404(Session, id=session_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'valider':
            session.statut_validation = 'validee'
            messages.success(request, f"Séance du {session.date} validée.")
        elif action == 'refuser':
            session.statut_validation = 'refusee'
            messages.warning(request, f"Séance du {session.date} refusée.")
        session.save()
        next_url = request.POST.get('next')
        if next_url:
            return redirect(next_url)
    return redirect('admin_sessions_list')


@admin_required
def admin_update_statut_session(request, session_id):
    """Endpoint AJAX — met à jour statut_validation d'une séance."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    session = get_object_or_404(Session, id=session_id)
    statut = request.POST.get('statut', '')
    valid_choices = dict(session._meta.get_field('statut_validation').choices)
    if statut not in valid_choices:
        return JsonResponse({'ok': False, 'error': 'Statut invalide'}, status=400)
    session.statut_validation = statut
    session.save(update_fields=['statut_validation'])
    label = valid_choices.get(statut, statut)
    return JsonResponse({'ok': True, 'statut': statut, 'label': label})


def _parse_date_range(request, default_days=14):
    today = timezone.now().date()
    date_debut_default = today - timedelta(days=default_days)
    try:
        date_debut = datetime.strptime(
            request.GET.get('date_debut', str(date_debut_default)), '%Y-%m-%d'
        ).date()
        date_fin = datetime.strptime(
            request.GET.get('date_fin', str(today)), '%Y-%m-%d'
        ).date()
    except ValueError:
        date_debut, date_fin = date_debut_default, today
    return date_debut, date_fin


# ─────────────────────────────────────────────────────────────
#  REPORTING PÉDAGOGIQUE
# ─────────────────────────────────────────────────────────────

@login_required
@admin_required
def admin_reporting_list(request):
    date_debut, date_fin = _parse_date_range(request)

    all_sessions = Session.objects.filter(
        date__gte=date_debut,
        date__lte=date_fin,
        seance_realisee=True,
    )

    teachers_stats = []
    for t in Teacher.objects.all().select_related('user'):
        t_sessions = all_sessions.filter(teacher=t)
        nb = t_sessions.count()
        if nb == 0:
            continue
        nb_validees = t_sessions.filter(statut_validation='validee').count()
        student_ids = t_sessions.values_list('students', flat=True).distinct()
        nb_students = student_ids.count()

        student_avgs = (
            t_sessions.filter(students__in=student_ids)
            .values('students')
            .annotate(
                avg_p=Avg('participation'),
                avg_c=Avg('comprehension_score'),
                avg_e=Avg('engagement'),
            )
        )
        nb_en_difficulte = sum(
            1 for row in student_avgs
            if (row['avg_p'] or 0) + (row['avg_c'] or 0) + (row['avg_e'] or 0) > 0
            and ((row['avg_p'] or 0) + (row['avg_c'] or 0) + (row['avg_e'] or 0)) / 3 < 2.5
        )

        comp_counts = {
            'Oral': t_sessions.filter(comp_oral=True).count(),
            'Compréhension': t_sessions.filter(comp_comprehension=True).count(),
            'Écrit': t_sessions.filter(comp_ecrit=True).count(),
            'Grammaire': t_sessions.filter(comp_grammaire=True).count(),
            'Vocabulaire': t_sessions.filter(comp_vocabulaire=True).count(),
        }
        top_comp = max(comp_counts, key=comp_counts.get) if any(comp_counts.values()) else None

        teachers_stats.append({
            'teacher': t,
            'nb_sessions': nb,
            'nb_sessions_validees': nb_validees,
            'nb_students': nb_students,
            'nb_en_difficulte': nb_en_difficulte,
            'top_comp_faible': top_comp,
        })

    return render(request, 'dashboard/admin/home/reporting.html', {
        'date_debut': date_debut,
        'date_fin': date_fin,
        'teachers_stats': teachers_stats,
        'total_sessions_global': sum(s['nb_sessions'] for s in teachers_stats),
        'total_teachers_actifs': len(teachers_stats),
        'total_students_global': all_sessions.values_list('students', flat=True).distinct().count(),
    })


@login_required
@admin_required
def admin_reporting_detail(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)

    date_debut, date_fin = _parse_date_range(request)

    sessions_qs = Session.objects.filter(
        teacher=teacher,
        date__gte=date_debut,
        date__lte=date_fin,
        seance_realisee=True,
    )

    total_sessions = sessions_qs.count()
    sessions_validees = sessions_qs.filter(statut_validation='validee').count()
    student_ids = sessions_qs.values_list('students', flat=True).distinct()
    students = Student.objects.filter(id__in=student_ids).select_related('user')

    student_stats = []
    students_en_difficulte = []
    for s in students:
        s_sessions = sessions_qs.filter(students=s)
        avg_participation = s_sessions.aggregate(Avg('participation'))['participation__avg']
        avg_comprehension = s_sessions.aggregate(Avg('comprehension_score'))['comprehension_score__avg']
        avg_engagement = s_sessions.aggregate(Avg('engagement'))['engagement__avg']
        stat = {
            'student': s,
            'nb_sessions': s_sessions.count(),
            'avg_participation': round(avg_participation, 1) if avg_participation else None,
            'avg_comprehension': round(avg_comprehension, 1) if avg_comprehension else None,
            'avg_engagement': round(avg_engagement, 1) if avg_engagement else None,
        }
        student_stats.append(stat)
        score = (avg_participation or 0) + (avg_comprehension or 0) + (avg_engagement or 0)
        if score > 0 and score / 3 < 2.5:
            students_en_difficulte.append(s)

    comp_faibles = {
        'Oral': sessions_qs.filter(comp_oral=True).count(),
        'Compréhension': sessions_qs.filter(comp_comprehension=True).count(),
        'Écrit': sessions_qs.filter(comp_ecrit=True).count(),
        'Grammaire': sessions_qs.filter(comp_grammaire=True).count(),
        'Vocabulaire': sessions_qs.filter(comp_vocabulaire=True).count(),
    }

    sessions_list = sessions_qs.select_related(
        'teacher__user', 'language'
    ).prefetch_related('students__user').order_by('-date', '-start_time')

    return render(request, 'dashboard/admin/home/reporting_detail.html', {
        'teacher': teacher,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'total_sessions': total_sessions,
        'sessions_validees': sessions_validees,
        'student_stats': student_stats,
        'students_en_difficulte': students_en_difficulte,
        'comp_faibles': comp_faibles,
        'sessions_list': sessions_list,
    })


@login_required
@teacher_required
def teacher_reporting(request):
    teacher = get_object_or_404(Teacher, user=request.user)

    date_debut, date_fin = _parse_date_range(request)

    sessions_qs = Session.objects.filter(
        teacher=teacher,
        date__gte=date_debut,
        date__lte=date_fin,
        seance_realisee=True,
    )

    total_sessions = sessions_qs.count()
    sessions_validees = sessions_qs.filter(statut_validation='validee').count()
    student_ids = sessions_qs.values_list('students', flat=True).distinct()
    students = Student.objects.filter(id__in=student_ids).select_related('user')

    student_stats = []
    students_en_difficulte = []
    for s in students:
        s_sessions = sessions_qs.filter(students=s)
        avg_participation = s_sessions.aggregate(Avg('participation'))['participation__avg']
        avg_comprehension = s_sessions.aggregate(Avg('comprehension_score'))['comprehension_score__avg']
        avg_engagement = s_sessions.aggregate(Avg('engagement'))['engagement__avg']
        stat = {
            'student': s,
            'nb_sessions': s_sessions.count(),
            'avg_participation': round(avg_participation, 1) if avg_participation else None,
            'avg_comprehension': round(avg_comprehension, 1) if avg_comprehension else None,
            'avg_engagement': round(avg_engagement, 1) if avg_engagement else None,
        }
        student_stats.append(stat)
        score = (avg_participation or 0) + (avg_comprehension or 0) + (avg_engagement or 0)
        if score > 0 and score / 3 < 2.5:
            students_en_difficulte.append(s)

    comp_faibles = {
        'Oral': sessions_qs.filter(comp_oral=True).count(),
        'Compréhension': sessions_qs.filter(comp_comprehension=True).count(),
        'Écrit': sessions_qs.filter(comp_ecrit=True).count(),
        'Grammaire': sessions_qs.filter(comp_grammaire=True).count(),
        'Vocabulaire': sessions_qs.filter(comp_vocabulaire=True).count(),
    }

    sessions_list = sessions_qs.select_related(
        'teacher__user', 'language'
    ).prefetch_related('students__user').order_by('-date', '-start_time')

    return render(request, 'dashboard/teacher/home/reporting.html', {
        'teacher': teacher,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'total_sessions': total_sessions,
        'sessions_validees': sessions_validees,
        'student_stats': student_stats,
        'students_en_difficulte': students_en_difficulte,
        'comp_faibles': comp_faibles,
        'sessions_list': sessions_list,
    })


# ─────────────────────────────────────────────────────────────
#  PAIEMENTS FORMATEURS (admin)
# ─────────────────────────────────────────────────────────────
@login_required
@admin_required
def paiements_formateurs_list(request):
    """Liste tous les paiements formateurs."""
    paiements = PaiementFormateur.objects.select_related('formateur__user').order_by('-created_at')

    statut = request.GET.get('statut', '')
    teacher_id = request.GET.get('teacher', '')
    if statut:
        paiements = paiements.filter(statut=statut)
    if teacher_id:
        paiements = paiements.filter(formateur_id=teacher_id)

    paginator = Paginator(paiements, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    total_en_attente = PaiementFormateur.objects.filter(statut='en_attente').aggregate(
        t=Sum('montant'))['t'] or 0
    total_paye = PaiementFormateur.objects.filter(statut='paye').aggregate(
        t=Sum('montant'))['t'] or 0

    return render(request, 'dashboard/admin/home/paiements_formateurs.html', {
        'paiements': page_obj,
        'teachers': Teacher.objects.all(),
        'statut_filter': statut,
        'teacher_filter': teacher_id,
        'total_en_attente': total_en_attente,
        'total_paye': total_paye,
    })

@login_required
@admin_required
def paiement_formateur_create(request):
    """Créer un nouveau paiement formateur."""
    if request.method == 'POST':
        form = PaiementFormateurForm(request.POST)
        if form.is_valid():
            paiement = form.save(commit=False)
            paiement.calculer_montant()
            paiement.save()
            messages.success(request, "Paiement formateur créé avec succès.")
            return redirect('paiements_formateurs_list')
    else:
        form = PaiementFormateurForm()

    return render(request, 'dashboard/admin/home/paiement_formateur_form.html', {
        'form': form,
        'titre': 'Créer un paiement',
    })

@login_required
@admin_required
def paiement_formateur_edit(request, paiement_id):
    """Modifier un paiement formateur existant."""
    paiement = get_object_or_404(PaiementFormateur, id=paiement_id)
    if request.method == 'POST':
        form = PaiementFormateurForm(request.POST, instance=paiement)
        if form.is_valid():
            p = form.save(commit=False)
            p.calculer_montant()
            p.save()
            messages.success(request, "Paiement mis à jour.")
            return redirect('paiements_formateurs_list')
    else:
        form = PaiementFormateurForm(instance=paiement)

    return render(request, 'dashboard/admin/home/paiement_formateur_form.html', {
        'form': form,
        'paiement': paiement,
        'titre': 'Modifier le paiement',
    })

@login_required
@admin_required
def paiement_formateur_delete(request, paiement_id):
    """Supprimer un paiement formateur."""
    paiement = get_object_or_404(PaiementFormateur, id=paiement_id)
    if request.method == 'POST':
        paiement.delete()
        messages.success(request, "Paiement supprimé.")
    return redirect('paiements_formateurs_list')


# ─────────────────────────────────────────────────────────────
#  MES PAIEMENTS (vue formateur)
# ─────────────────────────────────────────────────────────────

@login_required
def mes_paiements_formateur(request):
    """Vue formateur : ses paiements reçus et montants en attente."""
    if request.user.role != 'teacher':
        raise Http404
    teacher = get_object_or_404(Teacher, user=request.user)

    paiements = PaiementFormateur.objects.filter(formateur=teacher).order_by('-created_at')
    total_recu = paiements.filter(statut='paye').aggregate(t=Sum('montant'))['t'] or 0
    total_attente = paiements.filter(statut='en_attente').aggregate(t=Sum('montant'))['t'] or 0

    return render(request, 'dashboard/teacher/home/mes_paiements.html', {
        'paiements': paiements,
        'total_recu': total_recu,
        'total_attente': total_attente,
    })


# ─────────────────────────────────────────────────────────────
#  CERTIFICATS — vues améliorées
# ─────────────────────────────────────────────────────────────
@login_required
@admin_required
def admin_certificate_create(request):
    """Créer un certificat (admin) avec les nouveaux champs."""
    if request.method == 'POST':
        form = CertificateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Certificat créé avec succès.")
            return redirect('admin_certificates_list')
    else:
        form = CertificateForm()

    return render(request, 'dashboard/admin/home/certificate_form.html', {
        'form': form,
        'titre': 'Ajouter un certificat',
    })

@login_required
@admin_required
def admin_certificate_edit(request, cert_id):
    """Modifier un certificat existant."""
    cert = get_object_or_404(Certificate, id=cert_id)
    if request.method == 'POST':
        form = CertificateForm(request.POST, request.FILES, instance=cert)
        if form.is_valid():
            form.save()
            messages.success(request, "Certificat mis à jour.")
            return redirect('admin_certificates_list')
    else:
        form = CertificateForm(instance=cert)

    return render(request, 'dashboard/admin/home/certificate_form.html', {
        'form': form,
        'cert': cert,
        'titre': 'Modifier le certificat',
    })

@login_required
@admin_required
def admin_certificates_list(request):
    """Liste tous les certificats (admin)."""
    certs = Certificate.objects.select_related('student__user', 'language').order_by('-issued_date')
    return render(request, 'dashboard/admin/home/certificates_list.html', {
        'certs': certs,
    })


@admin_required
def admin_certificate_delete(request, cert_id):
    cert = get_object_or_404(Certificate, id=cert_id)
    if request.method == 'POST':
        cert.delete()
        messages.success(request, "Certificat supprimé.")
        return redirect('admin_certificates_list')
    return render(request, 'dashboard/admin/home/certificate_confirm_delete.html', {'cert': cert})


def certificate_public_view(request, certificate_id):
    """Page publique de vérification d'un certificat (sans connexion requise)."""
    try:
        cert = Certificate.objects.select_related('student__user', 'language').get(
            certificate_id=certificate_id,
            is_active=True,
        )
        valid = True
    except Certificate.DoesNotExist:
        cert = None
        valid = False

    return render(request, 'dashboard/public/certificate_verify.html', {
        'cert': cert,
        'valid': valid,
        'certificate_id': certificate_id,
    })


@login_required
def certificate_detail_student(request, cert_id):
    """Détail d'un certificat côté étudiant."""
    cert = get_object_or_404(Certificate, id=cert_id, is_active=True)
    if request.user.role == 'student':
        student = get_object_or_404(Student, user=request.user)
        if cert.student != student:
            raise Http404

    return render(request, 'dashboard/student/home/certificate_detail.html', {
        'cert': cert,
    })


# ═════════════════════════════════════════════════════════════
#  ADMIN DASHBOARD COMPLET — GESTION DE TOUS LES MODÈLES
# ═════════════════════════════════════════════════════════════
from .forms import (
    AdminUserCreateForm, AdminUserEditForm, AdminResetPasswordForm,
    StudentAdminForm, TeacherAdminForm, LanguageForm,
    SessionAdminForm, SessionSeriesAdminForm, PaymentAdminForm, EvaluationAdminForm,
    ResourceAdminForm, RequestAdminForm, NotificationAdminForm,
    AssignmentAdminForm,
)
from dashboard.models import Evaluation, Assignment, Submission, SessionSeries
from dashboard.services import generate_series_occurrences, apply_series_edit, apply_series_delete
from django.contrib.auth.hashers import make_password


# ─── HELPERS ──────────────────────────────────────────────────
def _admin_ctx(titre, section, back_url=None, **extra):
    ctx = {'titre': titre, 'section_active': section}
    if back_url:
        ctx['back_url'] = back_url
    ctx.update(extra)
    return ctx


# ═══════════════════════════════════════════════════════════════
#  1. GESTION DES UTILISATEURS
# ═══════════════════════════════════════════════════════════════

@admin_required
def admin_users_list(request):
    role = request.GET.get('role', '')
    search = request.GET.get('q', '')
    users = CustomUser.objects.select_related('user_profile').order_by('-date_joined')
    if role:
        users = users.filter(role=role)
    if search:
        users = users.filter(
            Q(username__icontains=search) | Q(first_name__icontains=search) |
            Q(last_name__icontains=search) | Q(email__icontains=search)
        )
    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/admin/home/users_list.html', {
        'users': page_obj, 'role_filter': role, 'search': search,
        'section_active': 'users',
    })


@admin_required
def admin_user_create(request):
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Utilisateur créé avec succès.")
            return redirect('admin_users_list')
    else:
        form = AdminUserCreateForm()
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        'Créer un utilisateur', 'users', 'admin_users_list', form=form,
    ))


@admin_required
def admin_user_edit(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Utilisateur mis à jour.")
            return redirect('admin_users_list')
    else:
        form = AdminUserEditForm(instance=user)
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        f'Modifier {user.username}', 'users', 'admin_users_list', form=form,
    ))


@admin_required
def admin_user_reset_password(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        form = AdminResetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password1'])
            user.save()
            messages.success(request, f"Mot de passe de {user.username} réinitialisé.")
            return redirect('admin_users_list')
    else:
        form = AdminResetPasswordForm()
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        f'Réinitialiser le mot de passe — {user.username}', 'users', 'admin_users_list', form=form,
    ))


@admin_required
def admin_user_toggle_active(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save()
        state = "activé" if user.is_active else "désactivé"
        messages.success(request, f"Compte {user.username} {state}.")
    return redirect('admin_users_list')


@admin_required
def admin_user_delete(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"Utilisateur {username} supprimé.")
        return redirect('admin_users_list')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': user, 'back_url': 'admin_users_list', 'section_active': 'users',
        'titre': f'Supprimer {user.username}',
    })


# ═══════════════════════════════════════════════════════════════
#  2. GESTION DES ÉTUDIANTS (CRUD COMPLET)
# ═══════════════════════════════════════════════════════════════

@admin_required
def admin_student_create(request):
    """Créer un étudiant : d'abord créer le compte user, puis le profil étudiant."""
    if request.method == 'POST':
        user_form = AdminUserCreateForm(request.POST)
        student_form = StudentAdminForm(request.POST)
        if user_form.is_valid() and student_form.is_valid():
            user = user_form.save(commit=False)
            user.role = 'student'
            user.save()  # signal creates Student via get_or_create
            student = Student.objects.get(user=user)
            student_form.instance = student
            student_form.save()
            messages.success(request, f"Étudiant {user.get_full_name()} créé.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect': reverse('admin_students')})
            return redirect('admin_students')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': user_form.errors | student_form.errors})
        messages.error(request, "Veuillez corriger les erreurs.")
    else:
        user_form = AdminUserCreateForm()
        student_form = StudentAdminForm()
    return render(request, 'dashboard/admin/home/student_form.html', {
        'user_form': user_form, 'student_form': student_form,
        'titre': 'Créer un étudiant', 'section_active': 'students',
    })


@admin_required
def admin_student_edit(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    user = student.user
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        user_form = AdminUserEditForm(request.POST, instance=user)
        student_form = StudentAdminForm(request.POST, instance=student)
        if user_form.is_valid() and student_form.is_valid():
            user_form.save()
            student_form.save()
            messages.success(request, "Étudiant mis à jour.")
            if is_ajax:
                return JsonResponse({'success': True, 'redirect': reverse('admin_students')})
            return redirect('student_detail', student_id=student.id)
        if is_ajax:
            return JsonResponse({'success': False, 'errors': user_form.errors | student_form.errors})
        messages.error(request, "Veuillez corriger les erreurs.")
    else:
        user_form = AdminUserEditForm(instance=user)
        student_form = StudentAdminForm(instance=student)
    return render(request, 'dashboard/admin/home/student_form.html', {
        'user_form': user_form, 'student_form': student_form,
        'titre': f'Modifier {user.get_full_name()}', 'section_active': 'students',
        'student': student,
    })


@admin_required
def admin_student_delete(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        name = str(student)
        student.user.delete()
        messages.success(request, f"{name} supprimé.")
        return redirect('admin_students')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': student, 'back_url': 'admin_students', 'section_active': 'students',
        'titre': f'Supprimer {student}',
    })


# ═══════════════════════════════════════════════════════════════
#  3. GESTION DES FORMATEURS (CRUD COMPLET)
# ═══════════════════════════════════════════════════════════════

@admin_required
def admin_teacher_create(request):
    if request.method == 'POST':
        user_form = AdminUserCreateForm(request.POST)
        teacher_form = TeacherAdminForm(request.POST)
        if user_form.is_valid() and teacher_form.is_valid():
            user = user_form.save(commit=False)
            user.role = 'teacher'
            user.save()  # signal creates Teacher via get_or_create
            teacher = Teacher.objects.get(user=user)
            teacher_form.instance = teacher
            teacher_form.save()
            messages.success(request, f"Formateur {user.get_full_name()} créé.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect': reverse('admin_teachers')})
            return redirect('admin_teachers')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': user_form.errors | teacher_form.errors})
        messages.error(request, "Veuillez corriger les erreurs.")
    else:
        user_form = AdminUserCreateForm()
        teacher_form = TeacherAdminForm()
    return render(request, 'dashboard/admin/home/teacher_form.html', {
        'user_form': user_form, 'teacher_form': teacher_form,
        'titre': 'Créer un formateur', 'section_active': 'teachers',
    })


@admin_required
def admin_teacher_edit(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    user = teacher.user
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        user_form = AdminUserEditForm(request.POST, instance=user)
        teacher_form = TeacherAdminForm(request.POST, instance=teacher)
        if user_form.is_valid() and teacher_form.is_valid():
            user_form.save()
            teacher_form.save()
            messages.success(request, "Formateur mis à jour.")
            if is_ajax:
                return JsonResponse({'success': True, 'redirect': reverse('admin_teachers')})
            return redirect('teacher_detail', teacher_id=teacher.id)
        if is_ajax:
            return JsonResponse({'success': False, 'errors': user_form.errors | teacher_form.errors})
        messages.error(request, "Veuillez corriger les erreurs.")
    else:
        user_form = AdminUserEditForm(instance=user)
        teacher_form = TeacherAdminForm(instance=teacher)
    return render(request, 'dashboard/admin/home/teacher_form.html', {
        'user_form': user_form, 'teacher_form': teacher_form,
        'titre': f'Modifier {user.get_full_name()}', 'section_active': 'teachers',
        'teacher': teacher,
    })


@admin_required
def admin_teacher_delete(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    if request.method == 'POST':
        name = str(teacher)
        teacher.user.delete()
        messages.success(request, f"{name} supprimé.")
        return redirect('admin_teachers')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': teacher, 'back_url': 'admin_teachers', 'section_active': 'teachers',
        'titre': f'Supprimer {teacher}',
    })


# ═══════════════════════════════════════════════════════════════
#  4. GESTION DES LANGUES
# ═══════════════════════════════════════════════════════════════

@admin_required
def admin_languages_list(request):
    languages = Language.objects.order_by('name')
    return render(request, 'dashboard/admin/home/languages_list.html', {
        'languages': languages, 'section_active': 'languages',
    })


@admin_required
def admin_language_create(request):
    if request.method == 'POST':
        form = LanguageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Langue créée.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect': reverse('admin_languages_list')})
            return redirect('admin_languages_list')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = LanguageForm()
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        'Ajouter une langue', 'languages', 'admin_languages_list', form=form,
    ))


@admin_required
def admin_language_edit(request, lang_id):
    lang = get_object_or_404(Language, id=lang_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        form = LanguageForm(request.POST, instance=lang)
        if form.is_valid():
            form.save()
            messages.success(request, "Langue mise à jour.")
            if is_ajax:
                return JsonResponse({'success': True, 'redirect': reverse('admin_languages_list')})
            return redirect('admin_languages_list')
        if is_ajax:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = LanguageForm(instance=lang)
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        f'Modifier {lang.name}', 'languages', 'admin_languages_list', form=form,
    ))


@admin_required
def admin_language_delete(request, lang_id):
    lang = get_object_or_404(Language, id=lang_id)
    if request.method == 'POST':
        lang.delete()
        messages.success(request, f"Langue {lang.name} supprimée.")
        return redirect('admin_languages_list')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': lang, 'back_url': 'admin_languages_list', 'section_active': 'languages',
        'titre': f'Supprimer {lang.name}',
    })


# ═══════════════════════════════════════════════════════════════
#  6. GESTION DES SÉANCES (CRUD COMPLET)
# ═══════════════════════════════════════════════════════════════

@admin_required
def admin_session_create(request):
    if request.method == 'POST':
        is_recurring = request.POST.get('is_recurring') == 'on'
        if is_recurring:
            form = SessionSeriesAdminForm(request.POST)
            if form.is_valid():
                series = form.save()
                occurrences = generate_series_occurrences(series)
                messages.success(request, f"Série créée — {len(occurrences)} séances générées.")
                return redirect('admin_sessions_list')
            return render(request, 'dashboard/admin/home/session_form.html', {
                'form': SessionAdminForm(),
                'series_form': form,
                'titre': 'Créer une séance',
                'section_active': 'sessions',
                'is_recurring': True,
            })
        else:
            form = SessionAdminForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Séance créée.")
                return redirect('admin_sessions_list')
    else:
        form = SessionAdminForm()
    return render(request, 'dashboard/admin/home/session_form.html', {
        'form': form,
        'series_form': SessionSeriesAdminForm(),
        'titre': 'Créer une séance',
        'section_active': 'sessions',
    })


@admin_required
def admin_session_edit(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if request.method == 'POST':
        scope = request.POST.get('_scope')
        form = SessionAdminForm(request.POST, instance=session)
        if form.is_valid():
            if scope and session.series_id:
                apply_series_edit(session, scope, form.cleaned_data)
                messages.success(request, f"Modification appliquée ({scope}).")
            else:
                form.save()
                messages.success(request, "Séance mise à jour.")
            return redirect('admin_sessions_list')
    else:
        form = SessionAdminForm(instance=session)
    return render(request, 'dashboard/admin/home/session_form.html', {
        'form': form,
        'series_form': SessionSeriesAdminForm(),
        'session': session,
        'titre': f'Modifier séance — {session.date}',
        'section_active': 'sessions',
    })


@admin_required
def admin_session_delete(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if request.method == 'POST':
        scope = request.POST.get('scope', 'this')
        if session.series_id:
            apply_series_delete(session, scope)
            messages.success(request, "Suppression appliquée.")
        else:
            session.delete()
            messages.success(request, "Séance supprimée.")
        return redirect('admin_sessions_list')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': session,
        'back_url': 'admin_sessions_list',
        'section_active': 'sessions',
        'titre': f'Supprimer la séance du {session.date}',
        'is_series': bool(session.series_id),
    })


@admin_required
def admin_session_scope_edit(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if request.method == 'POST':
        scope = request.POST.get('scope', 'this')
        form = SessionAdminForm(request.POST, instance=session)
        if form.is_valid():
            apply_series_edit(session, scope, form.cleaned_data)
            messages.success(request, "Modification appliquée.")
            return redirect('admin_sessions_list')
    else:
        scope = None
        form = SessionAdminForm(instance=session)
    return render(request, 'dashboard/admin/home/session_scope_choice.html', {
        'session': session, 'form': form, 'scope': scope,
        'section_active': 'sessions', 'titre': 'Portée de la modification',
    })


@admin_required
def admin_session_series_list(request):
    series_list = (
        SessionSeries.objects
        .select_related('teacher', 'language')
        .annotate(occurrences_count=Count('occurrences'))
        .order_by('-created_at')
    )
    return render(request, 'dashboard/admin/home/session_series_list.html', {
        'series_list': series_list, 'section_active': 'sessions', 'titre': 'Séries récurrentes',
    })


@admin_required
def admin_session_series_delete(request, series_id):
    series = get_object_or_404(SessionSeries, id=series_id)
    if request.method == 'POST':
        series.occurrences.all().delete()
        series.delete()
        messages.success(request, "Série et toutes ses séances supprimées.")
        return redirect('admin_session_series_list')
    count = series.occurrences.count()
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': series,
        'back_url': 'admin_session_series_list',
        'section_active': 'sessions',
        'titre': f'Supprimer la série — {count} séances seront effacées',
    })


# ═══════════════════════════════════════════════════════════════
#  7. GESTION DES PAIEMENTS ÉTUDIANTS
# ═══════════════════════════════════════════════════════════════

@admin_required
def admin_payments_list(request):
    status = request.GET.get('status', '')
    student_id = request.GET.get('student', '')
    payments = Payment.objects.select_related('student__user', 'languages').order_by('-payment_date')
    if status:
        payments = payments.filter(status=status)
    if student_id:
        payments = payments.filter(student_id=student_id)
    total = payments.filter(status='paid').aggregate(t=Sum('amount'))['t'] or 0
    paginator = Paginator(payments, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/admin/home/payments_list.html', {
        'payments': page_obj, 'students': Student.objects.all(),
        'status_filter': status, 'student_filter': student_id,
        'total_paye': total, 'section_active': 'payments',
    })


@admin_required
def admin_payment_create(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        form = PaymentAdminForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice_number = f"INV-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            payment.save()
            messages.success(request, "Paiement enregistré.")
            if is_ajax:
                return JsonResponse({'success': True, 'redirect': reverse('admin_payments_list')})
            return redirect('admin_payments_list')
        if is_ajax:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = PaymentAdminForm()
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        'Nouveau paiement étudiant', 'payments', 'admin_payments_list', form=form,
    ))


@admin_required
def admin_payment_edit(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        form = PaymentAdminForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, "Paiement mis à jour.")
            if is_ajax:
                return JsonResponse({'success': True, 'redirect': reverse('admin_payments_list')})
            return redirect('admin_payments_list')
        if is_ajax:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = PaymentAdminForm(instance=payment)
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        'Modifier le paiement', 'payments', 'admin_payments_list', form=form,
    ))


@admin_required
def admin_payment_delete(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    if request.method == 'POST':
        payment.delete()
        messages.success(request, "Paiement supprimé.")
        return redirect('admin_payments_list')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': payment, 'back_url': 'admin_payments_list', 'section_active': 'payments',
        'titre': 'Supprimer ce paiement',
    })


# ═══════════════════════════════════════════════════════════════
#  8. GESTION DES ÉVALUATIONS
# ═══════════════════════════════════════════════════════════════

@admin_required
def admin_evaluations_list(request):
    evals = Evaluation.objects.select_related('student__user', 'teacher__user', 'language').order_by('-evaluation_date')
    teacher_id = request.GET.get('teacher', '')
    if teacher_id:
        evals = evals.filter(teacher_id=teacher_id)
    paginator = Paginator(evals, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/admin/home/evaluations_list.html', {
        'evaluations': page_obj, 'teachers': Teacher.objects.all(),
        'teacher_filter': teacher_id, 'section_active': 'evaluations',
    })


@admin_required
def admin_evaluation_create(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        form = EvaluationAdminForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Évaluation créée.")
            if is_ajax:
                return JsonResponse({'success': True, 'redirect': reverse('admin_evaluations_list')})
            return redirect('admin_evaluations_list')
        if is_ajax:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = EvaluationAdminForm()
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        'Nouvelle évaluation', 'evaluations', 'admin_evaluations_list', form=form,
    ))


@admin_required
def admin_evaluation_edit(request, eval_id):
    ev = get_object_or_404(Evaluation, id=eval_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        form = EvaluationAdminForm(request.POST, instance=ev)
        if form.is_valid():
            form.save()
            messages.success(request, "Évaluation mise à jour.")
            if is_ajax:
                return JsonResponse({'success': True, 'redirect': reverse('admin_evaluations_list')})
            return redirect('admin_evaluations_list')
        if is_ajax:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = EvaluationAdminForm(instance=ev)
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        'Modifier l\'évaluation', 'evaluations', 'admin_evaluations_list', form=form,
    ))


@admin_required
def admin_evaluation_delete(request, eval_id):
    ev = get_object_or_404(Evaluation, id=eval_id)
    if request.method == 'POST':
        ev.delete()
        messages.success(request, "Évaluation supprimée.")
        return redirect('admin_evaluations_list')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': ev, 'back_url': 'admin_evaluations_list', 'section_active': 'evaluations',
        'titre': 'Supprimer cette évaluation',
    })


# ═══════════════════════════════════════════════════════════════
#  9. GESTION DES RESSOURCES
# ═══════════════════════════════════════════════════════════════

@admin_required
def admin_resources_list(request):
    resources = Resource.objects.select_related('teachers__user').order_by('-created_at')
    paginator = Paginator(resources, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/admin/home/resources_list.html', {
        'resources': page_obj, 'section_active': 'resources',
    })


@admin_required
def admin_resource_create(request):
    if request.method == 'POST':
        form = ResourceAdminForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Ressource créée.")
            return redirect('admin_resources_list')
    else:
        form = ResourceAdminForm()
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        'Ajouter une ressource', 'resources', 'admin_resources_list', form=form,
    ))


@admin_required
def admin_resource_edit(request, resource_id):
    res = get_object_or_404(Resource, id=resource_id)
    if request.method == 'POST':
        form = ResourceAdminForm(request.POST, request.FILES, instance=res)
        if form.is_valid():
            form.save()
            messages.success(request, "Ressource mise à jour.")
            return redirect('admin_resources_list')
    else:
        form = ResourceAdminForm(instance=res)
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        'Modifier la ressource', 'resources', 'admin_resources_list', form=form,
    ))


@admin_required
def admin_resource_delete(request, resource_id):
    res = get_object_or_404(Resource, id=resource_id)
    if request.method == 'POST':
        res.delete()
        messages.success(request, "Ressource supprimée.")
        return redirect('admin_resources_list')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': res, 'back_url': 'admin_resources_list', 'section_active': 'resources',
        'titre': f'Supprimer "{res.title}"',
    })


# ═══════════════════════════════════════════════════════════════
#  10. GESTION DES DEMANDES / REQUÊTES
# ═══════════════════════════════════════════════════════════════

@admin_required
def admin_requests_list(request):
    status = request.GET.get('status', '')
    reqs = Request.objects.select_related('student__user', 'teacher__user').order_by('-created_at')
    if status:
        reqs = reqs.filter(status=status)
    paginator = Paginator(reqs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/admin/home/requests_list.html', {
        'requests': page_obj, 'status_filter': status, 'section_active': 'requests',
    })


@admin_required
def admin_request_detail(request, req_id):
    req = get_object_or_404(Request, id=req_id)
    if request.method == 'POST':
        form = RequestAdminForm(request.POST, instance=req)
        if form.is_valid():
            form.save()
            messages.success(request, "Demande mise à jour.")
            return redirect('admin_requests_list')
    else:
        form = RequestAdminForm(instance=req)
    return render(request, 'dashboard/admin/home/request_detail.html', {
        'req': req, 'form': form, 'section_active': 'requests',
    })


@admin_required
def admin_request_delete(request, req_id):
    req = get_object_or_404(Request, id=req_id)
    if request.method == 'POST':
        req.delete()
        messages.success(request, "Demande supprimée.")
        return redirect('admin_requests_list')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': req, 'back_url': 'admin_requests_list', 'section_active': 'requests',
        'titre': 'Supprimer cette demande',
    })


# ═══════════════════════════════════════════════════════════════
#  11. GESTION DES NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

@admin_required
def admin_notifications_list(request):
    notifs = Notification.objects.select_related('user').order_by('-created_at')
    paginator = Paginator(notifs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/admin/home/notifications_list.html', {
        'notifs': page_obj, 'section_active': 'notifications',
    })


@admin_required
def admin_notification_create(request):
    if request.method == 'POST':
        form = NotificationAdminForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Notification envoyée.")
            return redirect('admin_notifications_list')
    else:
        form = NotificationAdminForm()
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        'Envoyer une notification', 'notifications', 'admin_notifications_list', form=form,
    ))


@admin_required
def admin_notification_delete(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id)
    if request.method == 'POST':
        notif.delete()
        messages.success(request, "Notification supprimée.")
        return redirect('admin_notifications_list')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': notif, 'back_url': 'admin_notifications_list', 'section_active': 'notifications',
        'titre': 'Supprimer cette notification',
    })


# ═══════════════════════════════════════════════════════════════
#  12. GESTION DES DEVOIRS
# ═══════════════════════════════════════════════════════════════

@admin_required
def admin_assignments_list(request):
    assignments = Assignment.objects.select_related('language').order_by('-created_at')
    paginator = Paginator(assignments, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/admin/home/assignments_list.html', {
        'assignments': page_obj, 'section_active': 'assignments',
    })


@admin_required
def admin_assignment_create(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        form = AssignmentAdminForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Devoir créé.")
            if is_ajax:
                return JsonResponse({'success': True, 'redirect': reverse('admin_assignments_list')})
            return redirect('admin_assignments_list')
        if is_ajax:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = AssignmentAdminForm()
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        'Créer un devoir', 'assignments', 'admin_assignments_list', form=form,
    ))


@admin_required
def admin_assignment_edit(request, assign_id):
    assign = get_object_or_404(Assignment, id=assign_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        form = AssignmentAdminForm(request.POST, instance=assign)
        if form.is_valid():
            form.save()
            messages.success(request, "Devoir mis à jour.")
            if is_ajax:
                return JsonResponse({'success': True, 'redirect': reverse('admin_assignments_list')})
            return redirect('admin_assignments_list')
        if is_ajax:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = AssignmentAdminForm(instance=assign)
    return render(request, 'dashboard/admin/home/admin_form.html', _admin_ctx(
        f'Modifier "{assign.title}"', 'assignments', 'admin_assignments_list', form=form,
    ))


@admin_required
def admin_assignment_delete(request, assign_id):
    assign = get_object_or_404(Assignment, id=assign_id)
    if request.method == 'POST':
        assign.delete()
        messages.success(request, "Devoir supprimé.")
        return redirect('admin_assignments_list')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': assign, 'back_url': 'admin_assignments_list', 'section_active': 'assignments',
        'titre': f'Supprimer "{assign.title}"',
    })


# ═══════════════════════════════════════════════════════════════
#  13. GESTION DES COMMENTAIRES
# ═══════════════════════════════════════════════════════════════

@admin_required
def admin_comments_list(request):
    comments = Comment.objects.select_related('teacher__user', 'language').order_by('-comment_at')
    paginator = Paginator(comments, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'dashboard/admin/home/comments_list.html', {
        'comments': page_obj, 'section_active': 'comments',
    })


@admin_required
def admin_comment_delete(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.method == 'POST':
        comment.delete()
        messages.success(request, "Commentaire supprimé.")
        return redirect('admin_comments_list')
    return render(request, 'dashboard/admin/home/confirm_delete.html', {
        'objet': comment, 'back_url': 'admin_comments_list', 'section_active': 'comments',
        'titre': 'Supprimer ce commentaire',
    })