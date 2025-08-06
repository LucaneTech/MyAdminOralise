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
# from .decorators import teacher_required, student_required
from dashboard.models import (
    CustomUser, Student, Teacher, Profile, 
    Skill, Mark, Schedule, Resource, Request, Assignment, 
    Submission, Attendance, Language, Session, Payment, Certificate, 
    Evaluation, Notification
)
from .forms import ProfileUpdateForm
import json


@login_required
def dashboard_view(request, username=None):
    # Si aucun username n'est fourni, utiliser celui de l'utilisateur connecté
    if username is None:
        username = request.user.username
    
    # If user is a teacher, redirect to teacher_view
    if request.user.role == 'teacher':
        return redirect('teacher_view', username=username)
    
    try:
        # Vérifier si l'utilisateur demandé existe
        requested_user = get_object_or_404(CustomUser, username=username)
        profile = get_object_or_404(Profile, user=requested_user)
        
        # Vérifier si l'utilisateur est un étudiant
        if requested_user.role != 'student':
            raise Http404("Cette page est réservée aux étudiants.")
        
        context = {
            'profile': profile,
            'user': request.user,
            'username': username,
        }
        
        student = get_object_or_404(Student, user=requested_user)
        today = timezone.now().date()
        
        # Informations principales selon le cahier des charges
        context.update({
            'student': student,
            'hours_remaining': student.hours_remaining,
            'total_hours_purchased': student.total_hours_purchased,
            'total_hours_used': student.total_hours_used,
            'languages': student.languages.all(),
            'current_teacher': student.current_teacher,
        })
        
        # Planning personnel (séances à venir)
        upcoming_sessions = student.upcoming_sessions
        context['upcoming_sessions'] = upcoming_sessions
        
        # Historique des séances (faites / reportées)
        completed_sessions = Session.objects.filter(
            student=student,
            status='completed'
        ).order_by('-date')[:10]
        context['completed_sessions'] = completed_sessions
        
        rescheduled_sessions = Session.objects.filter(
            student=student,
            status='rescheduled'
        ).order_by('-date')[:5]
        context['rescheduled_sessions'] = rescheduled_sessions
        
        # Séances du jour
        today_sessions = Session.objects.filter(
            student=student,
            date=today
        ).order_by('start_time')
        context['today_sessions'] = today_sessions
        
        # Notifications non lues
        unread_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')[:5]
        context['unread_notifications'] = unread_notifications
        
        # Certificats récents
        recent_certificates = Certificate.objects.filter(
            student=student,
            is_active=True
        ).order_by('-issued_date')[:3]
        context['recent_certificates'] = recent_certificates
        
        # Évaluations récentes
        recent_evaluations = Evaluation.objects.filter(
            student=student
        ).order_by('-evaluation_date')[:5]
        context['recent_evaluations'] = recent_evaluations
        
        # Statistiques de progression
        total_sessions = Session.objects.filter(student=student).count()
        completed_count = Session.objects.filter(student=student, status='completed').count()
        attendance_rate = (completed_count / total_sessions * 100) if total_sessions > 0 else 0
        
        context.update({
            'total_sessions': total_sessions,
            'completed_sessions_count': completed_count,
            'attendance_rate': round(attendance_rate, 2),
        })
        
        return render(request, 'dashboard/student/home/index.html', context)
        
    except Exception as e:
        messages.error(request, f"Erreur lors du chargement du dashboard: {str(e)}")
        return redirect('dashboard_home')


def teacher_view(request, username=None):
    if username is None:
        username = request.user.username
    
    try:
        requested_user = get_object_or_404(CustomUser, username=username)
        profile = get_object_or_404(Profile, user=requested_user)
        
        if requested_user.role != 'teacher':
            raise Http404("Cette page est réservée aux enseignants.")
        
        teacher = get_object_or_404(Teacher, user=requested_user)
        today = timezone.now().date()
        
        # Informations principales selon le cahier des charges
        context = {
            'profile': profile,
            'user': request.user,
            'username': username,
            'teacher': teacher,
            'languages': teacher.languages.all(),
            'total_students': teacher.total_students,
            'hourly_rate': teacher.hourly_rate,
            'is_available': teacher.is_available,
        }
        
        # Emploi du temps avec filtres par langue
        selected_language = request.GET.get('language')
        if selected_language:
            today_sessions = Session.objects.filter(
                teacher=teacher,
                date=today,
                language__code=selected_language
            ).order_by('start_time')
        else:
            today_sessions = teacher.today_sessions
        context['today_sessions'] = today_sessions
        context['selected_language'] = selected_language
        
        # Séances de la semaine
        weekly_sessions = teacher.weekly_sessions
        context['weekly_sessions'] = weekly_sessions
        
        # Séances récentes (faites)
        recent_completed_sessions = Session.objects.filter(
            teacher=teacher,
            status='completed'
        ).order_by('-date')[:10]
        context['recent_completed_sessions'] = recent_completed_sessions
        
        # Séances à cocher (prévues pour aujourd'hui)
        sessions_to_check = Session.objects.filter(
            teacher=teacher,
            date=today,
            status='scheduled'
        ).order_by('start_time')
        context['sessions_to_check'] = sessions_to_check
        
        # Séances reportées
        rescheduled_sessions = Session.objects.filter(
            teacher=teacher,
            status='rescheduled'
        ).order_by('-date')[:5]
        context['rescheduled_sessions'] = rescheduled_sessions
        
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
                status='completed'
            ).count()
            students_count = Student.objects.filter(
                current_teacher=teacher,
                languages=language
            ).count()
            
            language_stats.append({
                'language': language,
                'total_sessions': sessions_count,
                'completed_sessions': completed_count,
                'students_count': students_count,
                'completion_rate': (completed_count / sessions_count * 100) if sessions_count > 0 else 0
            })
        context['language_stats'] = language_stats
        
        # Évaluations récentes
        recent_evaluations = Evaluation.objects.filter(
            teacher=teacher
        ).order_by('-evaluation_date')[:5]
        context['recent_evaluations'] = recent_evaluations
        
        # Notifications
        unread_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')[:5]
        context['unread_notifications'] = unread_notifications
        
        return render(request, 'dashboard/teacher/home/index.html', context)
        
    except Exception as e:
        messages.error(request, f"Erreur lors du chargement du dashboard enseignant: {str(e)}")
        return redirect('dashboard_home')

# Vue pour afficher le profil (version fonction)


def profile_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=request.user)
    context = {
        'profile': profile,
        'user': request.user,
    }
    
    if user.role == 'student':
        student = get_object_or_404(Student, user=user)
        context['student'] = student
        return render(request, 'dashboard/student/home/profile.html', context)
    elif user.role == 'teacher':
        teacher = get_object_or_404(Teacher, user=user)
        context['teacher'] = teacher
        return render(request, 'dashboard/teacher/home/profile.html', context)
    


def profile_edit(request):
    user = request.user
    profile = get_object_or_404(Profile, user=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile_view')
    else:
        form = ProfileUpdateForm(instance=profile)
    context = { 
        'profile': profile,
        'form': form,
        'user': request.user,
     
    }
    if user.role == 'teacher':
        return render(request, 'dashboard/teacher/home/profile_edit.html', context)
    elif user.role == 'student':
        return render(request, 'dashboard/student/home/profile_edit.html', context)   
    


# Vue pour changer la photo de profil

@login_required
def update_profile_picture(request):
    if request.method == 'POST':
        profile = request.user.user_profile
        profile.profile_picture = request.FILES.get('profile_picture')
        profile.save()
        return redirect('profile_view')
    return render(request, 'profiles/update_picture.html')


@login_required
def schedule_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    context = {
        'profile': profile,
        'user': user,
        'username': user.username,
    }

    if user.role == 'student':
        student = get_object_or_404(Student, user=user)
        schedule = Schedule.objects.filter(skill__in=student.skill_set.all()).order_by('day', 'start_time')
        context['schedule'] = schedule 
        return render(request, 'dashboard/student/home/schedule.html', context)

    elif user.role == 'teacher':
        teacher = get_object_or_404(Teacher, user=user)
        schedule = Schedule.objects.filter(teacher=teacher).order_by('day', 'start_time')
        context['schedule'] = schedule  
        return render(request, 'dashboard/teacher/home/schedule.html', context)

    else:
        return render(request, '404.html', context)

def resources_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=request.user)
    context = {
        'profile': profile,
        'user': user,
        'username': request.user.username,
    }

    if user.role == 'student':
        student = get_object_or_404(Student, user=user)
        # Récupérer les ressources liées aux langues de l'étudiant
        student_languages = student.languages.all()
        resources = Resource.objects.filter(languages__in=student_languages).distinct()
        context.update({
            'resources': resources,
            'student': student
        })
        return render(request, 'dashboard/student/home/resources.html', context)
    
    elif user.role == 'teacher':
        teacher = get_object_or_404(Teacher, user=user)
        # Pour les enseignants, montrer les ressources qu'ils ont uploadées
        resources = Resource.objects.filter(uploaded_by=user)
        context.update({
            'resources': resources,
            'teacher': teacher
        })
        return render(request, 'dashboard/teacher/home/resources.html', context)



def requests_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    context = {
        'profile': profile,
        'user': user,
        'username': user.username,
    }

    if user.role == 'student':
        student = get_object_or_404(Student, user=user)
        
        # Traitement du formulaire de nouvelle demande
        if request.method == 'POST':
            request_type = request.POST.get('request_type')
            subject = request.POST.get('subject')
            description = request.POST.get('description')
            attachment = request.FILES.get('attachment')
            
            # Créer la nouvelle demande
            new_request = Request.objects.create(
                student=student,
                request_type=request_type,
                subject=subject,
                description=description,
                attachment=attachment
            )
            
            # Rediriger vers la même page pour éviter la soumission multiple
            return redirect('requests_view')
        
        # Récupérer toutes les demandes de l'étudiant
        requests = Request.objects.filter(student=student)
        
        # Statistiques des demandes
        total_requests = requests.count()
        pending_requests = requests.filter(status='pending').count()
        approved_requests = requests.filter(status='approved').count()
        rejected_requests = requests.filter(status='rejected').count()
        
        context.update({
            'requests': requests,
            'total_requests': total_requests,
            'pending_requests': pending_requests,
            'approved_requests': approved_requests,
            'rejected_requests': rejected_requests,
            'student': student
        })
        return render(request, 'dashboard/student/home/requests.html', context)
    
    elif user.role == 'teacher':
        teacher = get_object_or_404(Teacher, user=user)
        # Pour les enseignants, on pourrait montrer les demandes des étudiants de leurs classes
        context.update({
            'teacher': teacher
        })
        return render(request, 'dashboard/teacher/home/requests.html', context)



def dashboard_search(request):
    query = request.GET.get('q', '')
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    context = {
        'profile': profile,
        'user': user,
        'username': user.username,
        'query': query,
    }

    if user.role == 'student':
        student = get_object_or_404(Student, user=user)
        if query:
            # Recherche dans les compétences
            skills = student.skill_set.filter(
                Q(name__icontains=query)
            ).distinct()

            # Recherche dans les notes
            marks = Mark.objects.filter(
                Q(student=student) &
                (Q(skill__name__icontains=query))
            ).distinct()

            # Recherche dans les ressources
            resources = Resource.objects.filter(
                Q(skills__in=student.skill_set.all()) &
                (Q(title__icontains=query) |
                Q(description__icontains=query))
            ).distinct()

            # Recherche dans les demandes
            requests = Request.objects.filter(
                Q(student=student) &
                (Q(subject__icontains=query) |
                Q(description__icontains=query))
            ).distinct()

            # Recherche dans l'emploi du temps
            schedule_results = Schedule.objects.filter(
                Q(skill__in=student.skill_set.all()) &
                (Q(day__icontains=query) | Q(skill__name__icontains=query))
            ).distinct()

            context.update({
                'skills': skills,
                'marks': marks,
                'resources': resources,
                'requests': requests,
                'schedule': schedule_results,
                'student': student,
            })

        return render(request, 'dashboard/student/home/search_results.html', context)
    
    return redirect('dashboard_view')




def settings_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    
    if request.method == 'POST':
        # Traitement des paramètres
        theme = request.POST.get('theme', 'light')
        language = request.POST.get('language', 'fr')
        notifications = request.POST.get('notifications', 'all')
        email_notifications = request.POST.get('email_notifications', 'true')
        
        # Sauvegarder le thème dans la base de données
        profile.theme_preference = theme
        profile.save()
        
        # Sauvegarder les autres préférences dans la session
        request.session['language'] = language
        request.session['notifications'] = notifications
        request.session['email_notifications'] = email_notifications
        
        # Rediriger vers la même page
        return redirect('settings_view')
    
    # Récupérer les paramètres actuels
    context = {
        'profile': profile,
        'user': user,
        'username': user.username,
        'current_theme': profile.theme_preference,
        'current_language': request.session.get('language', 'fr'),
        'current_notifications': request.session.get('notifications', 'all'),
        'current_email_notifications': request.session.get('email_notifications', 'true'),
    }
    
    return render(request, 'dashboard/student/home/settings.html', context)

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
        'profile': profile,
        'skills': skills,
        'teacher': teacher,
        'user': user,
        'username': user.username,
        'segment': 'courses'
    }
    return render(request, 'dashboard/teacher/home/courses.html', context)



def teacher_schedule(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    schedule = Schedule.objects.filter(teacher=teacher)
    
    context = {
        'profile': profile,
        'teacher': teacher,
        'user': user,
        'username': user.username,
        'schedule': schedule,
        'segment': 'schedule'
    }
    return render(request, 'dashboard/teacher/home/schedule.html', context)


def teacher_assignments(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    skills = Skill.objects.filter(teachers=teacher)
    assignments = Assignment.objects.filter(skill__in=skills)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        assignment = Assignment.objects.create(
            title=data['title'],
            description=data['description'],
            skill_id=data['skill'],
            type=data['type'],
            due_date=data['due_date']
        )
        return JsonResponse({'status': 'success', 'id': assignment.id})
    
    context = {
        'profile': profile,
        'teacher': teacher,
        'user': user,
        'username': user.username,
        'assignments': assignments,
        'skills': skills,
        'segment': 'assignments'
    }
    return render(request, 'dashboard/teacher/home/assignments.html', context)


def teacher_students(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    skills = Skill.objects.filter(teachers=teacher)
    students = Student.objects.filter(skill__in=skills).distinct()
    
    context = {
        'profile': profile,
        'teacher': teacher,
        'user': user,
        'username': user.username,
        'students': students,
        'segment': 'students'
    }
    return render(request, 'dashboard/teacher/home/students.html', context)


def teacher_attendance(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    today = timezone.now().date()
    skills = Skill.objects.filter(teachers=teacher)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        skill_id = data['skill']
        date = data['date']
        attendances = data['attendances']
        
        for student_id, attendance_data in attendances.items():
            Attendance.objects.update_or_create(
                skill_id=skill_id,
                student_id=student_id,
                date=date,
                defaults={
                    'status': attendance_data['status'],
                    'arrival_time': attendance_data.get('arrival_time'),
                    'note': attendance_data.get('note')
                }
            )
        return JsonResponse({'status': 'success'})
    
    students = Student.objects.filter(skill__in=skills).distinct()
    
    # Statistiques de présence
    attendance_stats = Attendance.objects.filter(
        skill__in=skills
    ).values('status').annotate(count=Count('id'))
    
    # Évolution des présences sur la semaine
    week_stats = []
    for i in range(7):
        date = today - timedelta(days=i)
        presence = Attendance.objects.filter(
            skill__in=skills,
            date=date,
            status='present'
        ).count()
        total = Attendance.objects.filter(
            skill__in=skills,
            date=date
        ).count()
        if total > 0:
            percentage = (presence / total) * 100
        else:
            percentage = 0
        week_stats.append({
            'date': date.strftime('%a'),
            'percentage': percentage
        })
    
    context = {
        'profile': profile,
        'teacher': teacher,
        'user': user,
        'username': user.username,
        'skills': skills,
        'students': students,
        'attendance_stats': attendance_stats,
        'week_stats': week_stats,
        'segment': 'attendance'
    }
    return render(request, 'dashboard/teacher/home/attendance.html', context)


def teacher_marks(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    skills = Skill.objects.filter(teachers=teacher)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        mark = Mark.objects.create(
            student_id=data['student'],
            skill_id=data['skill'],
            mark=data['value']
        )
        
        # Si la note est liée à un devoir
        if 'assignment' in data:
            submission = Submission.objects.get(
                assignment_id=data['assignment'],
                student_id=data['student']
            )
            submission.mark = mark
            submission.save()
            
        return JsonResponse({'status': 'success', 'id': mark.id})
    
    marks = Mark.objects.filter(skill__in=skills)
    assignments = Assignment.objects.filter(skill__in=skills)
    
    context = {
        'profile': profile,
        'teacher': teacher,
        'user': user,
        'username': user.username,
        'marks': marks,
        'skills': skills,
        'assignments': assignments,
        'segment': 'marks'
    }   
    return render(request, 'dashboard/teacher/home/marks.html', context)


def teacher_skills(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    skills = Skill.objects.filter(teachers=teacher)
    
    # Récupérer les étudiants qui sont dans les matières de l'enseignant
    students = Student.objects.filter(skill__in=skills).distinct()
    
    context = {
        'profile': profile,
        'teacher': teacher,
        'user': user,
        'username': user.username,
        'skills': skills,
        'students': students,
        'segment': 'skills'
    }
    return render(request, 'dashboard/teacher/home/skills.html', context)

# API endpoints pour les actions AJAX


def api_filter_students(request):
    user = request.user
    teacher = get_object_or_404(Teacher, user=user)
    search = request.GET.get('search')
    
    skills = Skill.objects.filter(teachers=teacher)
    students = Student.objects.filter(skill__in=skills).distinct()
    
    if search:
        students = students.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    data = [{
        'id': student.id,
        'full_name': student.user.full_name,
        'email': student.user.email,
        'languages': [lang.name for lang in student.languages.all()],
        'matricule': student.matricule
    } for student in students]
    
    return JsonResponse(data, safe=False)


def api_filter_assignments(request):
    user = request.user
    profile = get_object_or_404(Profile, user=user)
    teacher = get_object_or_404(Teacher, user=user)
    skills = Skill.objects.filter(teachers=teacher)
    type_filter = request.GET.get('type')
    skill_id = request.GET.get('skill')
    status = request.GET.get('status')
    
    assignments = Assignment.objects.filter(skill__in=skills)
    
    if type_filter:
        assignments = assignments.filter(type=type_filter)
    if skill_id:
        assignments = assignments.filter(skill_id=skill_id)
    if status:
        assignments = assignments.filter(status=status)
    
    data = [{
        'profile': profile,
        'teacher': teacher,
        'user': user,
        'username': user.username,
        'id': assignment.id,
        'title': assignment.title,
        'description': assignment.description,
        'type': assignment.type,
        'status': assignment.status,
        'due_date': assignment.due_date.strftime('%d/%m/%Y'),
        'submissions_count': assignment.submissions.count()
    } for assignment in assignments]
    
    return JsonResponse(data, safe=False)

# Nouvelles vues pour le cahier des charges

@login_required
def session_detail_view(request, session_id):
    """Vue détaillée d'une séance avec possibilité de feedback"""
    session = get_object_or_404(Session, id=session_id)
    
    # Vérifier que l'utilisateur a accès à cette séance
    if request.user.role == 'student' and session.student.user != request.user:
        raise Http404("Accès non autorisé")
    elif request.user.role == 'teacher' and session.teacher.user != request.user:
        raise Http404("Accès non autorisé")
    
    if request.method == 'POST':
        feedback = request.POST.get('feedback')
        if feedback and request.user.role == 'teacher':
            session.feedback = feedback
            session.save()
            messages.success(request, "Feedback enregistré avec succès")
            return redirect('session_detail', session_id=session_id)
    
    context = {
        'session': session,
        'user': request.user,
    }
    
    # Choisir le bon template selon le rôle
    if request.user.role == 'student':
        return render(request, 'dashboard/student/home/session_detail.html', context)
    else:
        return render(request, 'dashboard/teacher/home/session_detail.html', context)

@login_required
def session_status_update(request, session_id):
    """Mise à jour du statut d'une séance (coche, report, absence)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    session = get_object_or_404(Session, id=session_id)
    
    # Vérifier que l'utilisateur est l'enseignant de cette séance
    if request.user.role != 'teacher' or session.teacher.user != request.user:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    new_status = request.POST.get('status')
    if new_status in ['completed', 'cancelled', 'rescheduled', 'absent']:
        session.status = new_status
        session.save()
        
        # Mettre à jour les heures utilisées si la séance est terminée
        if new_status == 'completed':
            student = session.student
            student.total_hours_used += session.duration_hours
            student.save()
        
        return JsonResponse({'success': True, 'status': new_status})
    
    return JsonResponse({'error': 'Statut invalide'}, status=400)

@login_required
def certificates_view(request):
    """Vue des certificats pour les étudiants"""
    if request.user.role != 'student':
        raise Http404("Cette page est réservée aux étudiants")
    
    student = get_object_or_404(Student, user=request.user)
    certificates = Certificate.objects.filter(student=student, is_active=True)
    
    context = {
        'certificates': certificates,
        'user': request.user,
    }
    return render(request, 'dashboard/student/home/certificates.html', context)

@login_required
def evaluations_view(request):
    """Vue des évaluations"""
    if request.user.role == 'student':
        student = get_object_or_404(Student, user=request.user)
        evaluations = Evaluation.objects.filter(student=student)
        return render(request, 'dashboard/student/home/evaluations.html', {
            'evaluations': evaluations,
            'user': request.user,
        })
    elif request.user.role == 'teacher':
        teacher = get_object_or_404(Teacher, user=request.user)
        evaluations = Evaluation.objects.filter(teacher=teacher)
        return render(request, 'dashboard/teacher/home/evaluations.html', {
            'evaluations': evaluations,
            'teacher': teacher,
            'user': request.user,
        })
    else:
        raise Http404("Accès non autorisé")

@login_required
def notifications_view(request):
    """Vue des notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id')
        if notification_id:
            notification = get_object_or_404(Notification, id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return JsonResponse({'success': True})
    
    context = {
        'notifications': notifications,
        'user': request.user,
    }
    
    # Choisir le bon template selon le rôle
    if request.user.role == 'student':
        return render(request, 'dashboard/student/home/notifications.html', context)
    else:
        return render(request, 'dashboard/teacher/home/notifications.html', context)

@login_required
def payments_view(request):
    """Vue des paiements pour les étudiants"""
    if request.user.role != 'student':
        raise Http404("Cette page est réservée aux étudiants")
    
    student = get_object_or_404(Student, user=request.user)
    payments = Payment.objects.filter(student=student)
    
    context = {
        'payments': payments,
        'student': student,
        'user': request.user,
    }
    return render(request, 'dashboard/student/home/payments.html', context)

@login_required
def teacher_sessions_view(request):
    """Vue des séances pour les enseignants avec filtres"""
    if request.user.role != 'teacher':
        raise Http404("Cette page est réservée aux enseignants")
    
    teacher = get_object_or_404(Teacher, user=request.user)
    
    # Filtres
    language_filter = request.GET.get('language')
    status_filter = request.GET.get('status')
    date_filter = request.GET.get('date')
    
    sessions = Session.objects.filter(teacher=teacher)
    
    if language_filter:
        sessions = sessions.filter(language__code=language_filter)
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    if date_filter:
        sessions = sessions.filter(date=date_filter)
    
    sessions = sessions.order_by('-date', '-start_time')
    
    context = {
        'sessions': sessions,
        'teacher': teacher,
        'languages': teacher.languages.all(),
        'status_choices': Session.STATUS_CHOICES,
        'filters': {
            'language': language_filter,
            'status': status_filter,
            'date': date_filter,
        },
        'user': request.user,
    }
    return render(request, 'dashboard/teacher/home/sessions.html', context)

@login_required
def student_sessions_view(request):
  
    """Vue des séances pour les étudiants"""
    if request.user.role != 'student':
        raise Http404("Cette page est réservée aux étudiants")
    
    student = get_object_or_404(Student, user=request.user)
    
    # Filtres
    status_filter = request.GET.get('status')
    date_filter = request.GET.get('date')
    
    sessions = Session.objects.filter(student=student)
    
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    if date_filter:
        sessions = sessions.filter(date=date_filter)
    
    sessions = sessions.order_by('-date', '-start_time')
    
    context = {  
        'sessions': sessions,
        'student': student,
        'status_choices': Session.STATUS_CHOICES,
        'filters': {
            'status': status_filter,
            'date': date_filter,
        },
        'user': request.user,
    }
    return render(request, 'dashboard/student/home/sessions.html', context)
