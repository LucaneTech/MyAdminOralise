from django import views
from django.urls import path
from .views import (
   
    add_request_response,
    add_schedule,
    admin_dashboard,
    admin_student_view,
    admin_teacher_view,
    
    delete_notification,
    delete_schedule,
    delete_student_session_by_id,
    edit_schedule,
    
    filter_schedule,
    get_resource_details,
    get_resource_form,
  
    load_schedule_week,
    notifications_mark_all_read,
    profile_view, 
    dashboard_view, profile_edit,
    quick_add_schedule, schedule_view,
    resources_view,resources_add, requests_view, 

    settings_view,
    student_detail_view,
    teacher_detail_view,

    teacher_resources_dashboard,
    teacher_schedule_view, teacher_view, teacher_courses, 
    teacher_assignments, teacher_students,
    api_filter_students, api_filter_assignments,
    session_detail_view, session_status_update, certificates_view,
    evaluations_view, notifications_view, payments_view,
    teacher_sessions_view, student_sessions_view,
  teacher_evaluations_add, 
    teacher_resources_add_student, evaluation_edit,
    export_students_csv, teacher_student_detail,
    update_request_status,
    update_request_status, 

 

)

urlpatterns = [
    path('teacher/courses/', teacher_courses, name='teacher_courses'),
    
    path('student/schedule', schedule_view, name= 'schedule_view' ),
    
    path('teacher/schedule/', teacher_schedule_view, name='teacher_schedule'),
    path('teacher/schedule/add/', add_schedule, name='add_schedule'),
    path('teacher/schedule/edit/<int:schedule_id>/', edit_schedule, name='edit_schedule'),
    path('teacher/schedule/delete/<int:schedule_id>/',delete_schedule, name='delete_schedule'),
    path('teacher/schedule/load-week/',load_schedule_week, name='load_schedule_week'),
    path('teacher/schedule/filter/',filter_schedule, name='filter_schedule'),
    path('teacher/schedule/quick-add/',quick_add_schedule, name='quick_add_schedule'),
    
    
    path('teacher/assignments/', teacher_assignments, name='teacher_assignments'),
    path('teacher/students/', teacher_students, name='teacher_students'),
    path('teacher/students/<int:student_id>/', teacher_student_detail, name='student_detail'),
    path('teacher/export-students/', export_students_csv, name='export_students'),
    
    path('teacher/resources/',teacher_resources_dashboard, name='teacher_resources_dashboard'),
    path('teacher/resources/details/<int:resource_id>/', get_resource_details, name='get_resource_details'),
    path('teacher/resources/add/', get_resource_form, name='get_resource_form'),
    
    
    path('teacher/sessions/', teacher_sessions_view, name='teacher_sessions'),
    path('teacher/sessions/delete/<int:session_id>/', delete_student_session_by_id, name='delete_student_session_by_id'),
    # path('teacher/sessions/update/<int:session_id>/', edit_session_view, name='edit_session'),
    
    path('teacher/evaluations/add/', teacher_evaluations_add, name='teacher_evaluations_add'),
    path('teacher/evaluations/<int:evaluation_id>/edit/', evaluation_edit, name='evaluation_edit'),
    path('teacher/<str:username>/', teacher_view, name='teacher_view'),
    
    # URLs communes
    path('profile/view/', profile_view, name='profile_view'), 
    path('profile/edit/', profile_edit, name='profile_edit'),
    # path('profile/update-picture/', update_profile_picture, name='update_picture'),
    
    path('settings/', settings_view, name='settings_view'),
    path('schedule/', schedule_view, name='schedule_view'),
    path('resources/', resources_view, name='resources_view'),
    path('requests/', requests_view, name='requests_view'),
    path('requests/update-status/', update_request_status, name='update_request_status'),
    path('requests/add-response/', add_request_response, name='add_request_response'),
    
    # Nouvelles URLs pour le cahier des charges
    path('session/<int:session_id>/', session_detail_view, name='session_detail'),
    path('session/<int:session_id>/status/', session_status_update, name='session_status_update'),
    path('certificates/', certificates_view, name='certificates_view'),
    path('evaluations/', evaluations_view, name='evaluations_view'),
    path('notifications/', notifications_view, name='notifications_view'),
    path('notifications/mark-read/', notifications_mark_all_read, name='notifications_mark_all_read'),
    path('notifications/delete/', delete_notification, name='delete_notification'),
    path('payments/', payments_view, name='payments_view'),
    path('sessions/', student_sessions_view, name='student_sessions'),
    
    
    # URLs étudiants
    path('student/<str:username>/', dashboard_view, name='dashboard_view'),
    
    # API endpoints
    path('api/filter-students/', api_filter_students, name='api_filter_students'),
    path('api/filter-assignments/', api_filter_assignments, name='api_filter_assignments'),
    
    
    #redirection
    path('', dashboard_view, name='dashboard_home'),
 
    path('administrateur/',admin_dashboard, name ="admin_dashboard"),
    path('administrateur/teachers/', admin_teacher_view, name='admin_teachers'),
    path('administrateur/teachers/<int:teacher_id>/', teacher_detail_view, name='teacher_detail'),
    path('administrateur/students/', admin_student_view, name='admin_students'),
    path('administrateur/students/<int:student_id>/', student_detail_view, name='student_detail'),
]



