from django.urls import path
from .views import (
    profile_view, update_profile_picture,
    dashboard_view, profile_edit, schedule_view, marks_view,
    skills_view, resources_view, requests_view, dashboard_search,
    settings_view, teacher_view, teacher_courses, teacher_schedule,
    teacher_assignments, teacher_students, teacher_attendance, teacher_marks,
    teacher_skills, api_filter_students, api_filter_assignments
)

urlpatterns = [
    # URLs enseignants (plus spécifiques en premier)
    path('teacher/courses/', teacher_courses, name='teacher_courses'),
    path('teacher/schedule/', teacher_schedule, name='teacher_schedule'),
    path('teacher/assignments/', teacher_assignments, name='teacher_assignments'),
    path('teacher/students/', teacher_students, name='teacher_students'),
    path('teacher/attendance/', teacher_attendance, name='teacher_attendance'),
    path('teacher/marks/', teacher_marks, name='teacher_marks'),
    path('teacher/skills/', teacher_skills, name='teacher_skills'),
    path('teacher/resources/', resources_view, name='teacher_resources'),
    path('teacher/<str:username>/', teacher_view, name='teacher_view'),
    
    # URLs communes
    path('profile/view/', profile_view, name='profile_view'),
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('profile/update-picture/', update_profile_picture, name='update_picture'),
    path('search/', dashboard_search, name='dashboard_search'),
    path('settings/', settings_view, name='settings_view'),
    path('schedule/', schedule_view, name='schedule_view'),
    path('marks/', marks_view, name='marks_view'),
    path('skills/', skills_view, name='skills_view'),
    path('resources/', resources_view, name='resources_view'),
    path('requests/', requests_view, name='requests_view'),
    
    # URLs étudiants
    path('student/<str:username>/', dashboard_view, name='dashboard_view'),
    
    # API endpoints
    path('api/filter-students/', api_filter_students, name='api_filter_students'),
    path('api/filter-assignments/', api_filter_assignments, name='api_filter_assignments'),
    
    # Redirection par défaut - will handle both student and teacher users
    path('', dashboard_view, name='dashboard_home'),
]

