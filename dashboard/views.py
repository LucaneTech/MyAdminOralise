import csv
from urllib import request
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import Http404, JsonResponse
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST


from dashboard.models import (
    CustomUser,
    Student,
    Teacher,
    Profile,
    Skill,
    Mark,
    Schedule,
    Resource,
    Request,
    Assignment,
    Submission,
    Attendance,
    Language,
    Session,
    Payment,
    Certificate,
    Evaluation,
    Notification,
    Comment,
)
from .forms import ProfileUpdateForm, ResourceForm, SessionForm
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
    if request.user.role == "preUser":
        return redirect("dashboard_home")

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
        attendance_rate = (
            (completed_count / total_sessions * 100) if total_sessions > 0 else 0
        )

        context.update(
            {
                "total_sessions": total_sessions,
                "completed_sessions_count": completed_count,
                "attendance_rate": round(attendance_rate, 2),
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
            "is_available": teacher.is_available,
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


@login_required
def schedule_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    context = {
        "profile": profile,
        "user": user,
        "username": user.username,
    }

    if user.role == "student":
        student = get_object_or_404(Student, user=user)
        # Récupérer les schedules liés aux compétences de l'étudiant
        schedule = Schedule.objects.filter(student=student).order_by(
            "day", "start_time"
        )
        context["schedule"] = schedule
        return render(request, "dashboard/student/home/schedule.html", context)

    elif user.role == "teacher":
        teacher = get_object_or_404(Teacher, user=user)
        schedule = Schedule.objects.filter(teacher=teacher).order_by(
            "day", "start_time"
        )
        context["schedule"] = schedule
        return render(request, "dashboard/teacher/home/schedule.html", context)

    else:
        return render(request, "404.html", context)


def resources_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=request.user)
    context = {
        "profile": profile,
        "user": user,
        "username": request.user.username,
    }

    if user.role == "student":
        student = get_object_or_404(Student, user=user)
        # Récupérer les ressources liées aux langues de l'étudiant
        student_languages = student.languages.all()
        resources = Resource.objects.filter(languages__in=student_languages).distinct()
        context.update({"resources": resources, "student": student})
        return render(request, "dashboard/student/home/resources.html", context)

    elif user.role == "teacher":
        teacher = get_object_or_404(Teacher, user=user)
        resources = Resource.objects.filter(uploaded_by=user)
        context.update({"resources": resources, "teacher": teacher})
        return render(request, "dashboard/teacher/home/resources.html", context)


@login_required
def resources_add(request):
    user = request.user
    if not hasattr(user, "teacher"):
        messages.error(request, "Page réservée aux enseignants.")
        return redirect("dashboard_home")
    teacher = get_object_or_404(Teacher, user=user)
    teacher_skills = Skill.objects.filter(teachers=teacher)
    if request.method == "POST":
        form = ResourceForm(request.POST, request.FILES)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.uploaded_by = user
            resource.save()
            # Ajoute les skills sélectionnés (liés à la branch)
            form.save_m2m()
            return redirect("teacher_resources")
    else:
        form = ResourceForm()
        # Limite les skills proposés à ceux du teacher
        form.fields["skills"].queryset = teacher_skills
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
#         skills = Skill.objects.filter(teachers=teacher)
#         total_skills = skills.count()
#         total_students = Student.objects.filter(skill__in=skills).distinct().count()
#         total_assignments = Assignment.objects.filter(skill__in=skills).count()

#         # Emploi du temps du jour
#         today_schedule = Schedule.objects.filter(
#             teacher=teacher,
#             day=today.strftime('%A')
#         ).order_by('start_time')

#         # Devoirs récents
#         recent_assignments = Assignment.objects.filter(
#             skill__in=skills
#         ).order_by('-created_at')[:5]

#         # Statistiques de présence
#         attendance_stats = Attendance.objects.filter(
#             skill__in=skills,
#             date=today
#         ).values('status').annotate(count=Count('id'))

#         # Notes récentes
#         recent_marks = Mark.objects.filter(
#             skill__in=skills
#         ).order_by('-id')[:5]

#         # Ressources récentes
#         recent_resources = Resource.objects.filter(
#             uploaded_by=requested_user
#         ).order_by('-created_at')[:5]

#         context = {
#             'profile': profile,
#             'user': request.user,
#             'username': username,
#             'teacher': teacher,
#             'total_skills': total_skills,
#             'total_students': total_students,
#             'total_assignments': total_assignments,
#             'today_schedule': today_schedule,
#             'recent_assignments': recent_assignments,
#             'attendance_stats': attendance_stats,
#             'recent_marks': recent_marks,
#             'recent_resources': recent_resources,
#             'skills': skills,
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
    skills = Skill.objects.filter(teachers=teacher)

    context = {
        "profile": profile,
        "skills": skills,
        "teacher": teacher,
        "user": user,
        "username": user.username,
        "segment": "courses",
    }
    return render(request, "dashboard/teacher/home/courses.html", context)


def teacher_schedule(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    schedule = Schedule.objects.filter(teacher=teacher)

    context = {
        "profile": profile,
        "teacher": teacher,
        "user": user,
        "username": user.username,
        "schedule": schedule,
        "segment": "schedule",
    }
    return render(request, "dashboard/teacher/home/schedule.html", context)


def teacher_assignments(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    skills = Skill.objects.filter(teachers=teacher)
    assignments = Assignment.objects.filter(skill__in=skills)

    if request.method == "POST":
        data = json.loads(request.body)
        assignment = Assignment.objects.create(
            title=data["title"],
            description=data["description"],
            skill_id=data["skill"],
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
        "skills": skills,
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

    # Calcul du taux de présence
    if total_sessions > 0:
        attendance_rate = (completed_sessions / total_sessions) * 100
    else:
        attendance_rate = 0

    context = {
        "profile": profile,
        "teacher": teacher,
        "user": request.user,
        "student": student,
        "recent_sessions": recent_sessions,
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "attendance_rate": round(attendance_rate, 1),
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

def teacher_attendance(request):
    user = request.user

    # Vérifier si l'utilisateur est bien un enseignant
    if not hasattr(user, "teacher"):
        messages.error(request, "Page réservée aux enseignants.")
        return redirect("dashboard_home")

    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    today = timezone.now().date()

    # Récupérer les compétences de l'enseignant
    skills = Skill.objects.filter(teachers=teacher)

    # Si l'enseignant enregistre des présences
    if request.method == "POST":
        data = json.loads(request.body)
        skill_id = data["skill"]
        date = data["date"]
        attendances = data["attendances"]

        for student_id, attendance_data in attendances.items():
            Attendance.objects.update_or_create(
                skill_id=skill_id,
                student_id=student_id,
                date=date,
                defaults={
                    "status": attendance_data["status"],
                    "arrival_time": attendance_data.get("arrival_time"),
                    "note": attendance_data.get("note"),
                },
            )
        return JsonResponse({"status": "success"})

    # Correction ici : utiliser current_teacher au lieu de languages
    students = Student.objects.filter(current_teachers=teacher).distinct()

    # Statistiques globales de présence
    attendance_stats = (
        Attendance.objects.filter(skill__in=skills)
        .values("status")
        .annotate(count=Count("id"))
    )

    # Statistiques par jour sur la semaine
    week_stats = []
    for i in range(7):
        date = today - timedelta(days=i)
        presence = Attendance.objects.filter(
            skill__in=skills, date=date, status="present"
        ).count()
        total = Attendance.objects.filter(skill__in=skills, date=date).count()

        percentage = (presence / total) * 100 if total > 0 else 0

        week_stats.append({"date": date.strftime("%a"), "percentage": percentage})

    context = {
        "profile": profile,
        "teacher": teacher,
        "user": user,
        "username": user.username,
        "skills": skills,
        "students": students,
        "attendance_stats": attendance_stats,
        "week_stats": week_stats,
        "segment": "attendance",
    }

    return render(request, "dashboard/teacher/home/attendance.html", context)


def teacher_marks(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    skills = Skill.objects.filter(teachers=teacher)

    if request.method == "POST":
        data = json.loads(request.body)
        mark = Mark.objects.create(
            student_id=data["student"], skill_id=data["skill"], mark=data["value"]
        )

        # Si la note est liée à un devoir
        if "assignment" in data:
            submission = Submission.objects.get(
                assignment_id=data["assignment"], student_id=data["student"]
            )
            submission.mark = mark
            submission.save()

        return JsonResponse({"status": "success", "id": mark.id})

    marks = Mark.objects.filter(skill__in=skills)
    assignments = Assignment.objects.filter(skill__in=skills)

    context = {
        "profile": profile,
        "teacher": teacher,
        "user": user,
        "username": user.username,
        "marks": marks,
        "skills": skills,
        "assignments": assignments,
        "segment": "marks",
    }
    return render(request, "dashboard/teacher/home/marks.html", context)


def teacher_skills(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    skills = Skill.objects.filter(teachers=teacher)

    # Récupérer les étudiants qui ont cet enseignant comme current_teacher
    students = Student.objects.filter(current_teacher=teacher).distinct()

    context = {
        "profile": profile,
        "teacher": teacher,
        "user": user,
        "username": user.username,
        "skills": skills,
        "students": students,
        "segment": "skills",
    }
    return render(request, "dashboard/teacher/home/skills.html", context)


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
    skills = Skill.objects.filter(teachers=teacher)
    type_filter = request.GET.get("type")
    skill_id = request.GET.get("skill")
    status = request.GET.get("status")

    assignments = Assignment.objects.filter(skill__in=skills)

    if type_filter:
        assignments = assignments.filter(type=type_filter)
    if skill_id:
        assignments = assignments.filter(skill_id=skill_id)
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
def teacher_schedule_manage(request):
    """Vue pour gérer l'emploi du temps de l'enseignant"""
    if request.user.role != "teacher":
        raise Http404("Cette page est réservée aux enseignants")

    teacher = get_object_or_404(Teacher, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            # Ajouter un nouveau cours
            day = request.POST.get("day")
            skill_id = request.POST.get("skill")
            student_id = request.POST.get("student")
            start_time = request.POST.get("start_time")
            end_time = request.POST.get("end_time")
            classroom = request.POST.get("classroom")

            try:
                skill = get_object_or_404(Skill, id=skill_id)
                student = (
                    get_object_or_404(Student, id=student_id) if student_id else None
                )

                Schedule.objects.create(
                    day=day,
                    skill=skill,
                    student=student,
                    teacher=teacher,
                    classroom=classroom,
                    start_time=start_time,
                    end_time=end_time,
                )
                messages.success(request, "Cours ajouté avec succès")
            except Exception as e:
                messages.error(request, f"Erreur lors de l'ajout: {str(e)}")

        elif action == "edit":
            # Modifier un cours existant
            schedule_id = request.POST.get("schedule_id")
            try:
                schedule = get_object_or_404(Schedule, id=schedule_id, teacher=teacher)
                schedule.day = request.POST.get("day")
                schedule.skill = get_object_or_404(Skill, id=request.POST.get("skill"))
                schedule.student = (
                    get_object_or_404(Student, id=request.POST.get("student"))
                    if request.POST.get("student")
                    else None
                )
                schedule.start_time = request.POST.get("start_time")
                schedule.end_time = request.POST.get("end_time")
                schedule.classroom = request.POST.get("classroom")
                schedule.save()
                messages.success(request, "Cours modifié avec succès")
            except Exception as e:
                messages.error(request, f"Erreur lors de la modification: {str(e)}")

        elif action == "delete":
            # Supprimer un cours
            schedule_id = request.POST.get("schedule_id")
            try:
                schedule = get_object_or_404(Schedule, id=schedule_id, teacher=teacher)
                schedule.delete()
                messages.success(request, "Cours supprimé avec succès")
            except Exception as e:
                messages.error(request, f"Erreur lors de la suppression: {str(e)}")

        schedules = Schedule.objects.filter(teacher=teacher).order_by(
            "day", "start_time"
        )
    skills = Skill.objects.filter(teachers=teacher)
    students = Student.objects.filter(current_teacher=teacher)

    context = {
        "schedules": schedules,
        "skills": skills,
        "students": students,
        "teacher": teacher,
        "profile": profile,
        "user": request.user,
        "day_choices": Schedule.DAY_CHOICES,
    }

    return render(request, "dashboard/teacher/home/schedule_manage.html", context)


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
def teacher_attendance_manage(request):
    """Vue pour gérer les présences des étudiants"""
    if request.user.role != "teacher":
        raise Http404("Cette page est réservée aux enseignants")

    teacher = get_object_or_404(Teacher, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == "POST":
        try:
            date = request.POST.get("date")
            skill_id = request.POST.get("skill")
            attendance_data = request.POST.getlist("attendance")
            student_ids = request.POST.getlist("student_id")
            statuses = request.POST.getlist("status")
            arrival_times = request.POST.getlist("arrival_time")
            notes = request.POST.getlist("note")

            skill = get_object_or_404(Skill, id=skill_id)

            # Mettre à jour ou créer les présences
            for i, student_id in enumerate(student_ids):
                if student_id:
                    student = get_object_or_404(Student, id=student_id)
                    status = statuses[i] if i < len(statuses) else "present"
                    arrival_time = (
                        arrival_times[i]
                        if i < len(arrival_times) and arrival_times[i]
                        else None
                    )
                    note = notes[i] if i < len(notes) else ""

                    attendance, created = Attendance.objects.get_or_create(
                        student=student,
                        skill=skill,
                        date=date,
                        defaults={
                            "status": status,
                            "arrival_time": arrival_time,
                            "note": note,
                        },
                    )

                    if not created:
                        attendance.status = status
                        attendance.arrival_time = arrival_time
                        attendance.note = note
                        attendance.save()

            messages.success(request, "Présences enregistrées avec succès")

        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement: {str(e)}")

    # Récupérer les données pour le formulaire
    selected_date = request.GET.get("date", timezone.now().date())
    selected_skill = request.GET.get("skill")

    skills = Skill.objects.filter(teachers=teacher)
    students = Student.objects.filter(current_teacher=teacher)

    # Récupérer les présences existantes pour la date et la matière sélectionnées
    existing_attendance = {}
    if selected_date and selected_skill:
        skill = get_object_or_404(Skill, id=selected_skill)
        attendance_records = Attendance.objects.filter(skill=skill, date=selected_date)
        for record in attendance_records:
            existing_attendance[record.student.id] = record

    context = {
        "skills": skills,
        "students": students,
        "selected_date": selected_date,
        "selected_skill": selected_skill,
        "existing_attendance": existing_attendance,
        "attendance_statuses": Attendance.STATUS,
        "teacher": teacher,
        "profile": profile,
        "user": request.user,
    }

    return render(request, "dashboard/teacher/home/attendance_manage.html", context)


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
            skill_id = request.POST.get("skill")

            # Gérer le fichier ou l'URL
            file = request.FILES.get("file")
            url = request.POST.get("url")

            student = get_object_or_404(Student, id=student_id)
            language = get_object_or_404(Language, id=language_id)
            skill = get_object_or_404(Skill, id=skill_id) if skill_id else None

            resource = Resource.objects.create(
                title=title,
                description=description,
                resource_type=resource_type,
                file=file,
                url=url,
                uploaded_by=request.user,
            )

            # Ajouter les relations
            resource.languages.add(language)
            if skill:
                resource.skills.add(skill)

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
    skills = Skill.objects.filter(teachers=teacher)
    resource_types = Resource.RESOURCE_TYPES

    context = {
        "students": students,
        "languages": languages,
        "skills": skills,
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


@login_required
def teacher_schedule_enhanced(request):
    """Vue améliorée pour l'emploi du temps avec affichage Google Calendar-like"""
    if request.user.role != "teacher":
        raise Http404("Cette page est réservée aux enseignants")

    teacher = get_object_or_404(Teacher, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)

    # Récupérer la date sélectionnée (par défaut aujourd'hui)
    selected_date = request.GET.get("date")
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    # Récupérer la semaine contenant la date sélectionnée
    start_of_week = selected_date - timedelta(days=selected_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Récupérer l'emploi du temps de la semaine
    weekly_schedule = (
        Schedule.objects.filter(teacher=teacher, is_active=True)
        .select_related("skill", "language", "student")
        .order_by("day", "start_time")
    )

    # Organiser l'emploi du temps par jour
    schedule_by_day = {}
    for day in Schedule.DAY_CHOICES:
        schedule_by_day[day[0]] = []

    for schedule in weekly_schedule:
        if schedule.day in schedule_by_day:
            schedule_by_day[schedule.day].append(schedule)

    # Récupérer les séances du jour sélectionné
    today_sessions = (
        Session.objects.filter(teacher=teacher, date=selected_date, status="scheduled")
        .select_related("student", "language")
        .order_by("start_time")
    )

    # Récupérer les présences du jour
    today = timezone.now().date()
    today_sessions_for_attendance = Session.objects.filter(
        teacher=teacher, date=today, status="scheduled"
    )

    # Créer un dictionnaire des présences par étudiant et matière
    attendance_dict = {}
    attendances = Attendance.objects.filter(teacher=teacher, date=today).select_related(
        "student", "skill", "session"
    )

    for attendance in attendances:
        key = (attendance.student.id, attendance.skill.id)
        attendance_dict[key] = attendance

    today_attendance = {
        "sessions": today_sessions_for_attendance,
        "attendances": attendance_dict,
        "date": today,
    }

    # Statistiques par langue pour la semaine
    language_stats = {}
    for schedule in weekly_schedule:
        if schedule.language:
            lang_name = schedule.language.name
            if lang_name not in language_stats:
                language_stats[lang_name] = {
                    "total_hours": 0,
                    "sessions_count": 0,
                    "students_count": 0,
                    "color_class": schedule.color_class,
                }
            language_stats[lang_name]["total_hours"] += schedule.duration_minutes / 60
            language_stats[lang_name]["sessions_count"] += 1
            if schedule.student:
                language_stats[lang_name]["students_count"] += 1

    context = {
        "teacher": teacher,
        "profile": profile,
        "user": request.user,
        "username": request.user.username,
        "selected_date": selected_date,
        "start_of_week": start_of_week,
        "end_of_week": end_of_week,
        "schedule_by_day": schedule_by_day,
        "today_sessions": today_sessions,
        "today_attendance": today_attendance,
        "language_stats": language_stats,
        "day_choices": Schedule.DAY_CHOICES,
        "segment": "schedule_enhanced",
    }

    return render(request, "dashboard/teacher/home/schedule_enhanced.html", context)


@login_required
def teacher_attendance_dynamic(request):
    """Vue pour la gestion dynamique des présences basée sur les séances du jour"""
    if request.user.role != "teacher":
        raise Http404("Cette page est réservée aux enseignants")

    teacher = get_object_or_404(Teacher, user=request.user)
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            date = data.get("date")
            session_id = data.get("session_id")
            attendance_data = data.get("attendance_data", {})

            if not date or not session_id:
                return JsonResponse(
                    {"status": "error", "message": "Date et session requises"}
                )

            # Convertir la date
            try:
                date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse(
                    {"status": "error", "message": "Format de date invalide"}
                )

            # Récupérer la session
            session = get_object_or_404(Session, id=session_id, teacher=teacher)

            # Mettre à jour ou créer les présences
            for student_id, attendance_info in attendance_data.items():
                student = get_object_or_404(Student, id=student_id)
                status = attendance_info.get("status", "present")
                arrival_time = attendance_info.get("arrival_time")
                note = attendance_info.get("note", "")

                # Convertir l'heure d'arrivée si fournie
                if arrival_time:
                    try:
                        arrival_time = datetime.strptime(arrival_time, "%H:%M").time()
                    except ValueError:
                        arrival_time = None

                # Trouver la compétence correspondant à la langue de la session
                skill = Skill.objects.filter(
                    name__icontains=session.language.name, teachers=teacher
                ).first()

                if not skill:
                    # Créer une compétence par défaut si elle n'existe pas
                    skill = Skill.objects.create(
                        name=f"{session.language.name} - Cours",
                        description=f"Cours de {session.language.name}",
                    )
                    skill.teachers.add(teacher)

                # Mettre à jour ou créer la présence
                attendance, created = Attendance.objects.update_or_create(
                    student=student,
                    skill=skill,
                    teacher=teacher,
                    date=date,
                    session=session,
                    defaults={
                        "status": status,
                        "arrival_time": arrival_time,
                        "note": note,
                    },
                )

                if not created:
                    attendance.status = status
                    attendance.arrival_time = arrival_time
                    attendance.note = note
                    attendance.save()

            return JsonResponse(
                {"status": "success", "message": "Présences mises à jour"}
            )

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    # Récupérer la date sélectionnée
    selected_date = request.GET.get("date")
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    # Récupérer les séances du jour pour cet enseignant
    today_sessions = (
        Session.objects.filter(teacher=teacher, date=selected_date, status="scheduled")
        .select_related("student", "language")
        .order_by("start_time")
    )

    # Récupérer les présences existantes
    existing_attendance = {}
    for session in today_sessions:
        attendances = Attendance.objects.filter(
            session=session, date=selected_date
        ).select_related("student")

        for attendance in attendances:
            if attendance.student.id not in existing_attendance:
                existing_attendance[attendance.student.id] = {}
            existing_attendance[attendance.student.id][session.id] = attendance

    # Récupérer tous les étudiants de cet enseignant
    teacher_students = (
        Student.objects.filter(current_teacher=teacher)
        .select_related("user")
        .order_by("user__first_name")
    )

    context = {
        "teacher": teacher,
        "profile": profile,
        "user": request.user,
        "username": request.user.username,
        "selected_date": selected_date,
        "today_sessions": today_sessions,
        "existing_attendance": existing_attendance,
        "teacher_students": teacher_students,
        "attendance_statuses": Attendance.STATUS,
        "segment": "attendance_dynamic",
    }

    return render(request, "dashboard/teacher/home/attendance_dynamic.html", context)


@login_required
def teacher_schedule_api(request):
    """API pour récupérer l'emploi du temps au format JSON pour FullCalendar"""
    if request.user.role != "teacher":
        return JsonResponse({"error": "Accès non autorisé"}, status=403)

    teacher = get_object_or_404(Teacher, user=request.user)

    # Récupérer les paramètres de date
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")

    if not start_date or not end_date:
        return JsonResponse({"error": "Dates de début et fin requises"}, status=400)

    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Format de date invalide"}, status=400)

    # Récupérer l'emploi du temps pour la période
    schedules = Schedule.objects.filter(teacher=teacher, is_active=True).select_related(
        "skill", "language", "student"
    )

    # Convertir en format FullCalendar
    events = []
    for schedule in schedules:
        # Calculer la prochaine occurrence de ce cours
        current_date = start_date
        while current_date <= end_date:
            # Trouver le prochain jour de la semaine correspondant
            while current_date.weekday() != _get_weekday_number(schedule.day):
                current_date += timedelta(days=1)
                if current_date > end_date:
                    break

            if current_date <= end_date:
                # Créer l'événement
                event = {
                    "id": f"schedule_{schedule.id}_{current_date}",
                    "title": f"{schedule.skill.name} - {schedule.language_name if schedule.language else 'N/A'}",
                    "start": f"{current_date}T{schedule.start_time}",
                    "end": f"{current_date}T{schedule.end_time}",
                    "className": schedule.color_class,
                    "extendedProps": {
                        "schedule_id": schedule.id,
                        "skill_name": schedule.skill.name,
                        "language_name": schedule.language_name,
                        "classroom": schedule.classroom or "",
                        "student_name": (
                            schedule.student.user.get_full_name()
                            if schedule.student
                            else "Groupe"
                        ),
                        "duration": schedule.duration_minutes,
                    },
                }
                events.append(event)

                # Passer à la semaine suivante
                current_date += timedelta(days=7)

    return JsonResponse(events, safe=False)


def _get_weekday_number(day_name):
    """Convertit le nom du jour en numéro de jour de la semaine (0=Lundi, 6=Dimanche)"""
    day_mapping = {
        "Lundi": 0,
        "Mardi": 1,
        "Mercredi": 2,
        "Jeudi": 3,
        "Vendredi": 4,
        "Samedi": 5,
        "Dimanche": 6,
    }
    return day_mapping.get(day_name, 0)
