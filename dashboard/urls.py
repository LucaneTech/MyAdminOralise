from django.urls import path
from .views import (
    profile_view, update_profile_picture,
    dashboard_view, profile_edit, schedule_view,
    resources_view,resources_add, requests_view, dashboard_search,
    settings_view, teacher_view, teacher_courses, teacher_schedule,
    teacher_assignments, teacher_students, teacher_attendance, teacher_marks,
    teacher_skills, api_filter_students, api_filter_assignments,
    session_detail_view, session_status_update, certificates_view,
    evaluations_view, notifications_view, payments_view,
    teacher_sessions_view, student_sessions_view,
    teacher_schedule_manage, teacher_evaluations_add, teacher_attendance_manage,
    teacher_resources_add_student, evaluation_edit,
    teacher_schedule_enhanced, teacher_schedule_api, teacher_attendance_dynamic,create_session_view
    
)

urlpatterns = [
    path('teacher/courses/', teacher_courses, name='teacher_courses'),
    path('teacher/schedule/', teacher_schedule, name='teacher_schedule'),
    path('teacher/schedule/enhanced/', teacher_schedule_enhanced, name='teacher_schedule_enhanced'),
    path('teacher/schedule/manage/', teacher_schedule_manage, name='teacher_schedule_manage'),
    path('teacher/schedule/api/', teacher_schedule_api, name='teacher_schedule_api'),
    path('teacher/assignments/', teacher_assignments, name='teacher_assignments'),
    path('teacher/students/', teacher_students, name='teacher_students'),
    path('teacher/attendance/', teacher_attendance, name='teacher_attendance'),
    path('teacher/attendance/dynamic/', teacher_attendance_dynamic, name='teacher_attendance_dynamic'),
    path('teacher/attendance/manage/', teacher_attendance_manage, name='teacher_attendance_manage'),
    path('teacher/marks/', teacher_marks, name='teacher_marks'),
    path('teacher/skills/', teacher_skills, name='teacher_skills'),
    path('teacher/resources/', resources_view, name='teacher_resources'),
    path('teacher/resources_add/',resources_add, name= 'teacher_resources_add'),
    path('teacher/resources/add/student/', teacher_resources_add_student, name='teacher_resources_add_student'),
    path('teacher/sessions/', teacher_sessions_view, name='teacher_sessions'),
    path('teacher/evaluations/add/', teacher_evaluations_add, name='teacher_evaluations_add'),
    path('teacher/evaluations/<int:evaluation_id>/edit/', evaluation_edit, name='evaluation_edit'),
    path('teacher/<str:username>/', teacher_view, name='teacher_view'),
    
    # URLs communes
    path('profile/view/', profile_view, name='profile_view'),
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('profile/update-picture/', update_profile_picture, name='update_picture'),
    path('search/', dashboard_search, name='dashboard_search'),
    path('settings/', settings_view, name='settings_view'),
    path('schedule/', schedule_view, name='schedule_view'),
    path('resources/', resources_view, name='resources_view'),
    path('requests/', requests_view, name='requests_view'),
    
    # Nouvelles URLs pour le cahier des charges
    path('session/<int:session_id>/', session_detail_view, name='session_detail'),
    path('session/<int:session_id>/status/', session_status_update, name='session_status_update'),
    path('certificates/', certificates_view, name='certificates_view'),
    path('evaluations/', evaluations_view, name='evaluations_view'),
    path('notifications/', notifications_view, name='notifications_view'),
    path('payments/', payments_view, name='payments_view'),
    path('sessions/', student_sessions_view, name='student_sessions'),
    path('sessions/create/', create_session_view, name='create_session'),
    
    # URLs étudiants
    path('student/<str:username>/', dashboard_view, name='dashboard_view'),
    
    # API endpoints
    path('api/filter-students/', api_filter_students, name='api_filter_students'),
    path('api/filter-assignments/', api_filter_assignments, name='api_filter_assignments'),
    
    
    #redirection
    path('', dashboard_view, name='dashboard_home'),
]

