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
    CustomUser, Student, Teacher, Profile, Branch, 
    Skill, Mark, Schedule, Resource, Request, Assignment, 
    Submission, Attendance
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
        
        # Nombre total de matières
        total_skills = Skill.objects.filter(students=student).count()
        
        # Nombre total d'étudiants dans les mêmes branches
        total_students = Student.objects.filter(branch__in=student.branch.all()).distinct().count()
        
        # Emploi du temps du jour
        from datetime import datetime
        DAYS_MAPPING = {
            'Monday': 'Lundi',
            'Tuesday': 'Mardi',
            'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi',
            'Friday': 'Vendredi',
            'Saturday': 'Samedi',
            'Sunday': 'Dimanche'
        }
        today_name = DAYS_MAPPING[datetime.now().strftime('%A')]
        
        today_schedule = Schedule.objects.filter(
            branch__in=student.branch.all(),
            day=today_name
        ).order_by('start_time')
        
        # Notes récentes
        recent_marks = Mark.objects.filter(student=student).order_by('-id')[:5]
        
        # Performance moyenne
        average_performance = Mark.objects.filter(student=student).aggregate(Avg('mark'))['mark__avg']
        if average_performance:
            average_performance = round(average_performance, 2)
        else:
            average_performance = 0
        
        # Matières du jour
        today_skills = Skill.objects.filter(
            schedule__branch__in=student.branch.all(),
            schedule__day=today_name
        ).distinct()
        
        context.update({
            'total_skills': total_skills,
            'total_students': total_students,
            'today_schedule': today_schedule,
            'recent_marks': recent_marks,
            'average_performance': average_performance,
            'today_skills': today_skills,
            'student': student,
        })
        
        return render(request, 'dashboard/student/home/index.html', context)
            
    except Http404:
        messages.error(request, "Cet utilisateur n'existe pas ou n'a pas les permissions nécessaires.")
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
        
        # Récupération des statistiques via les propriétés du modèle
        total_skills = teacher.total_courses
        total_students = teacher.total_students
        total_assignments = teacher.total_assignments
        
        # Emploi du temps du jour
        today_schedule = Schedule.objects.filter(
            teacher=teacher,
            day=today.strftime('%A')
        ).order_by('start_time')
        
        # Devoirs récents et à venir
        recent_assignments = Assignment.objects.filter(
            skill__in=teacher.skill_set.all()
        ).order_by('-created_at')[:5]
        
        upcoming_assignments = Assignment.objects.filter(
            skill__in=teacher.skill_set.all(),
            due_date__gt=today,
            status='published'
        ).order_by('due_date')[:5]
        
        # Statistiques de présence du mois
        attendance_stats = teacher.monthly_attendance_stats
        
        # Performance moyenne de la classe
        class_performance = teacher.class_performance
        
        # Évolution des présences sur la semaine
        week_stats = []
        for i in range(7):
            date = today - timedelta(days=i)
            presence = Attendance.objects.filter(
                skill__in=teacher.skill_set.all(),
                date=date,
                status='present'
            ).count()
            total = Attendance.objects.filter(
                skill__in=teacher.skill_set.all(),
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
        
        # Notes récentes
        recent_marks = Mark.objects.filter(
            skill__in=teacher.skill_set.all()
        ).select_related('student', 'skill').order_by('-created_at')[:10]
        
        # Statistiques par matière
        skills_stats = []
        for skill in teacher.skill_set.all():
            stats = {
                'name': skill.name,
                'average': float(skill.average_mark),
                'students_count': skill.students.count(),
                'assignments_count': Assignment.objects.filter(skill=skill).count(),
                'attendance_rate': float(Attendance.objects.filter(
                    skill=skill,
                    date__gte=today.replace(day=1),
                    status='present'
                ).count() / max(Attendance.objects.filter(
                    skill=skill,
                    date__gte=today.replace(day=1)
                ).count(), 1) * 100)
            }
            skills_stats.append(stats)
        
        context = {
            'profile': profile,
            'user': request.user,
            'username': username,
            'teacher': teacher,
            'total_skills': total_skills,
            'total_students': total_students,
            'total_assignments': total_assignments,
            'today_schedule': today_schedule,
            'recent_assignments': recent_assignments,
            'upcoming_assignments': upcoming_assignments,
            'attendance_stats': attendance_stats,
            'class_performance': class_performance,
            'week_stats': week_stats,
            'recent_marks': recent_marks,
            'skills_stats': skills_stats,
            'skills_stats_json': json.dumps(skills_stats),
            'segment': 'index'
        }
        
        return render(request, 'dashboard/teacher/home/index.html', context)
            
    except Http404:
        messages.error(request, "Cet utilisateur n'existe pas ou n'a pas les permissions nécessaires.")
        return redirect('dashboard_home')

# Vue pour afficher le profil (version fonction)


def profile_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=request.user)
    context = {
        'profile': profile,
        'user': request.user,
        
    }
    if user.role == 'teacher':
        return render(request, 'dashboard/teacher/home/profile.html', context)
    elif user.role == 'student':
       
        return render(request, 'dashboard/student/home/profile.html', context)
    


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
        schedule = Schedule.objects.filter(branch__in=student.branch.all()).order_by('day', 'start_time')
        context['schedule'] = schedule 
        return render(request, 'dashboard/student/home/schedule.html', context)

    elif user.role == 'teacher':
        teacher = get_object_or_404(Teacher, user=user)
        schedule = Schedule.objects.filter(teacher=teacher).order_by('day', 'start_time')
        context['schedule'] = schedule  
        return render(request, 'dashboard/teacher/home/schedule.html', context)

    else:
        return render(request, '404.html', context)



def marks_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=request.user)
    context = {
        'profile': profile,
        'user': user,
        'username': request.user.username,
    }

    if user.role == 'student':
        student = get_object_or_404(Student, user=user)
        
        # Récupérer toutes les notes de l'étudiant
        marks = Mark.objects.filter(student=student)
        
        # Calculer la moyenne générale
        average = marks.aggregate(Avg('mark'))['mark__avg']
        if average is not None:
            average = round(average, 2)
        else:
            average = 0
            
        # Nombre total d'étudiants dans les mêmes branches
        total_students = Student.objects.filter(branch__in=student.branch.all()).distinct().count()
        
        # Nombre de matières avec notes
        subjects_with_marks = marks.values('skill').distinct().count()
        
        # Nombre total de matières
        total_subjects = student.skill_set.count()
        
        # Meilleures et pires notes
        best_mark = marks.order_by('-mark').first() if marks.exists() else None
        worst_mark = marks.order_by('mark').first() if marks.exists() else None
        
        # Notes par matière
        marks_by_subject = {}
        for mark in marks:
            if mark.skill.name not in marks_by_subject:
                marks_by_subject[mark.skill.name] = []
            marks_by_subject[mark.skill.name].append(mark.mark)
        
        # Calculer la moyenne par matière
        subjects_averages = {}
        for subject, subject_marks in marks_by_subject.items():
            subjects_averages[subject] = round(sum(subject_marks) / len(subject_marks), 2)
        
        context.update({
            'marks': marks,
            'average': average,
            'total_students': total_students,
            'subjects_with_marks': subjects_with_marks,
            'total_subjects': total_subjects,
            'best_mark': best_mark,
            'worst_mark': worst_mark,
            'subjects_averages': subjects_averages,
            'student': student
        })
        
        return render(request, 'dashboard/student/home/marks.html', context)
    
    elif user.role == 'teacher':
        teacher = get_object_or_404(Teacher, user=user)
        skills = teacher.skill_set.all()
        marks = Mark.objects.filter(skill__in=skills)
        context['marks'] = marks
        return render(request, 'dashboard/teacher/home/marks.html', context)



def skills_view(request):
    user = request.user
    profile = get_object_or_404(Profile, user=request.user)
    context = {
        'profile': profile,
        'user': user,
        'username': request.user.username,
    }
    

    if user.role == 'student':
        student = get_object_or_404(Student, user=user)
        skills = student.skill_set.all()
        context['skills'] = skills
        return render(request, 'dashboard/student/home/skills.html', context)
    
    elif user.role == 'teacher':
        teacher = get_object_or_404(Teacher, user=user)
        skills = teacher.skill_set.all()
        context['skills'] = skills
        return render(request, 'dashboard/teacher/home/skills.html', context)



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
        # Récupérer les ressources liées aux compétences de l'étudiant
        student_skills = student.skill_set.all()
        resources = Resource.objects.filter(skills__in=student_skills).distinct()
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
            schedule = Schedule.objects.filter(
                Q(branch__in=student.branch.all()) &
                (Q(skill__name__icontains=query) |
                Q(teacher__user__first_name__icontains=query) |
                Q(teacher__user__last_name__icontains=query) |
                Q(classroom__icontains=query))
            ).distinct()

            context.update({
                'skills': skills,
                'marks': marks,
                'resources': resources,
                'requests': requests,
                'schedule': schedule,
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
    branches = Branch.objects.filter(student__in=students).distinct()
    
    context = {
        'profile': profile,
        'teacher': teacher,
        'user': user,
        'username': user.username,
        'students': students,
        'branches': branches,
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
    
    # Récupérer les branches des étudiants qui sont dans les matières de l'enseignant
    students = Student.objects.filter(skill__in=skills).distinct()
    branches = Branch.objects.filter(student__in=students).distinct()
    
    context = {
        'profile': profile,
        'teacher': teacher,
        'user': user,
        'username': user.username,
        'skills': skills,
        'branches': branches,
        'segment': 'skills'
    }
    return render(request, 'dashboard/teacher/home/skills.html', context)

# API endpoints pour les actions AJAX


def api_filter_students(request):
    user = request.user
    teacher = get_object_or_404(Teacher, user=user)
    branch_id = request.GET.get('branch')
    search = request.GET.get('search')
    
    skills = Skill.objects.filter(teachers=teacher)
    students = Student.objects.filter(skill__in=skills).distinct()
    
    if branch_id:
        students = students.filter(branch=branch_id)
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
        'branches': [b.name for b in student.branch.all()],
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
