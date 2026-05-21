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
    resource_create,
    resource_delete,
    resource_edit,
    resources_view,
    teacher_resources_dashboard,
    load_schedule_week,
    notifications_mark_all_read,
    profile_view,
    dashboard_view, profile_edit,
    quick_add_schedule, schedule_view,
    requests_view,
    settings_view,
    student_detail_view,
    teacher_detail_view,
    teacher_schedule_view, teacher_view, teacher_courses,
    teacher_assignments, teacher_students,
    api_filter_students, api_filter_assignments,
    session_detail_view, session_status_update, certificates_view,
    evaluations_view, notifications_view, payments_view,
    teacher_sessions_view, student_sessions_view,
    teacher_evaluations_add,
    evaluation_edit,
    export_students_csv, teacher_student_detail,
    update_request_status,
    # Nouvelles vues
    fiche_pedagogique_edit,
    fiche_pedagogique_detail,
    admin_sessions_list,
    admin_valider_session,
    reporting_formateur,
    paiements_formateurs_list,
    paiement_formateur_create,
    paiement_formateur_edit,
    paiement_formateur_delete,
    mes_paiements_formateur,
    admin_certificate_create,
    admin_certificate_edit,
    admin_certificates_list,
    certificate_public_view,
    certificate_detail_student,
    # Dashboard admin complet
    admin_users_list, admin_user_create, admin_user_edit,
    admin_user_reset_password, admin_user_toggle_active, admin_user_delete,
    admin_student_create, admin_student_edit, admin_student_delete,
    admin_teacher_create, admin_teacher_edit, admin_teacher_delete,
    admin_languages_list, admin_language_create, admin_language_edit, admin_language_delete,
    admin_schedules_list, admin_schedule_create, admin_schedule_edit, admin_schedule_delete,
    admin_session_create, admin_session_edit, admin_session_delete,
    admin_payments_list, admin_payment_create, admin_payment_edit, admin_payment_delete,
    admin_evaluations_list, admin_evaluation_create, admin_evaluation_edit, admin_evaluation_delete,
    admin_resources_list, admin_resource_create, admin_resource_edit, admin_resource_delete,
    admin_requests_list, admin_request_detail, admin_request_delete,
    admin_notifications_list, admin_notification_create, admin_notification_delete,
    admin_assignments_list, admin_assignment_create, admin_assignment_edit, admin_assignment_delete,
    admin_comments_list, admin_comment_delete,
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
    path('teacher/students/<int:student_id>/', teacher_student_detail, name='teacher_student_detail'),
    path('teacher/export-students/', export_students_csv, name='export_students'),
    
    path('teacher/resources/',teacher_resources_dashboard, name='teacher_resources_dashboard'),
    path('ressources/create/', resource_create, name='resource_create'),
    path('ressources/<int:resource_id>/update/', resource_edit, name='resource_edit'),
    path('ressources/<int:resource_id>/delete/', resource_delete, name='resource_delete'),
   
  
    
    
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
 
    path('administrateur/', admin_dashboard, name='admin_dashboard'),
    path('administrateur/teachers/', admin_teacher_view, name='admin_teachers'),
    path('administrateur/teachers/<int:teacher_id>/', teacher_detail_view, name='teacher_detail'),
    path('administrateur/students/', admin_student_view, name='admin_students'),
    path('administrateur/students/<int:student_id>/', student_detail_view, name='student_detail'),

    # Fiches pédagogiques
    path('session/<int:session_id>/fiche/', fiche_pedagogique_edit, name='fiche_pedagogique_edit'),
    path('session/<int:session_id>/fiche/detail/', fiche_pedagogique_detail, name='fiche_pedagogique_detail'),

    # Validation séances (admin)
    path('administrateur/seances/', admin_sessions_list, name='admin_sessions_list'),
    path('administrateur/seances/<int:session_id>/valider/', admin_valider_session, name='admin_valider_session'),

    # Reporting
    path('reporting/', reporting_formateur, name='reporting_formateur'),
    path('administrateur/reporting/<int:teacher_id>/', reporting_formateur, name='admin_reporting_formateur'),

    # Paiements formateurs (admin)
    path('administrateur/paiements-formateurs/', paiements_formateurs_list, name='paiements_formateurs_list'),
    path('administrateur/paiements-formateurs/creer/', paiement_formateur_create, name='paiement_formateur_create'),
    path('administrateur/paiements-formateurs/<int:paiement_id>/modifier/', paiement_formateur_edit, name='paiement_formateur_edit'),
    path('administrateur/paiements-formateurs/<int:paiement_id>/supprimer/', paiement_formateur_delete, name='paiement_formateur_delete'),

    # Mes paiements (formateur)
    path('teacher/mes-paiements/', mes_paiements_formateur, name='mes_paiements_formateur'),

    # Certificats (admin)
    path('administrateur/certificats/', admin_certificates_list, name='admin_certificates_list'),
    path('administrateur/certificats/ajouter/', admin_certificate_create, name='admin_certificate_create'),
    path('administrateur/certificats/<int:cert_id>/modifier/', admin_certificate_edit, name='admin_certificate_edit'),

    # Certificat détail (étudiant)
    path('certificats/<int:cert_id>/detail/', certificate_detail_student, name='certificate_detail_student'),

    # Page publique de vérification (sans connexion)
    path('certificat/<str:certificate_id>/', certificate_public_view, name='certificate_public_view'),

    # ── DASHBOARD ADMIN COMPLET ─────────────────────────────────

    # Utilisateurs
    path('administrateur/utilisateurs/', admin_users_list, name='admin_users_list'),
    path('administrateur/utilisateurs/creer/', admin_user_create, name='admin_user_create'),
    path('administrateur/utilisateurs/<int:user_id>/modifier/', admin_user_edit, name='admin_user_edit'),
    path('administrateur/utilisateurs/<int:user_id>/mdp/', admin_user_reset_password, name='admin_user_reset_password'),
    path('administrateur/utilisateurs/<int:user_id>/activer/', admin_user_toggle_active, name='admin_user_toggle_active'),
    path('administrateur/utilisateurs/<int:user_id>/supprimer/', admin_user_delete, name='admin_user_delete'),

    # Étudiants CRUD
    path('administrateur/students/creer/', admin_student_create, name='admin_student_create'),
    path('administrateur/students/<int:student_id>/modifier/', admin_student_edit, name='admin_student_edit'),
    path('administrateur/students/<int:student_id>/supprimer/', admin_student_delete, name='admin_student_delete'),

    # Formateurs CRUD
    path('administrateur/teachers/creer/', admin_teacher_create, name='admin_teacher_create'),
    path('administrateur/teachers/<int:teacher_id>/modifier/', admin_teacher_edit, name='admin_teacher_edit'),
    path('administrateur/teachers/<int:teacher_id>/supprimer/', admin_teacher_delete, name='admin_teacher_delete'),

    # Langues
    path('administrateur/langues/', admin_languages_list, name='admin_languages_list'),
    path('administrateur/langues/creer/', admin_language_create, name='admin_language_create'),
    path('administrateur/langues/<int:lang_id>/modifier/', admin_language_edit, name='admin_language_edit'),
    path('administrateur/langues/<int:lang_id>/supprimer/', admin_language_delete, name='admin_language_delete'),

    # Plannings
    path('administrateur/plannings/', admin_schedules_list, name='admin_schedules_list'),
    path('administrateur/plannings/creer/', admin_schedule_create, name='admin_schedule_create'),
    path('administrateur/plannings/<int:sched_id>/modifier/', admin_schedule_edit, name='admin_schedule_edit'),
    path('administrateur/plannings/<int:sched_id>/supprimer/', admin_schedule_delete, name='admin_schedule_delete'),

    # Séances CRUD
    path('administrateur/seances/creer/', admin_session_create, name='admin_session_create'),
    path('administrateur/seances/<int:session_id>/modifier/', admin_session_edit, name='admin_session_edit'),
    path('administrateur/seances/<int:session_id>/supprimer/', admin_session_delete, name='admin_session_delete'),

    # Paiements étudiants
    path('administrateur/paiements/', admin_payments_list, name='admin_payments_list'),
    path('administrateur/paiements/creer/', admin_payment_create, name='admin_payment_create'),
    path('administrateur/paiements/<int:payment_id>/modifier/', admin_payment_edit, name='admin_payment_edit'),
    path('administrateur/paiements/<int:payment_id>/supprimer/', admin_payment_delete, name='admin_payment_delete'),

    # Évaluations
    path('administrateur/evaluations/', admin_evaluations_list, name='admin_evaluations_list'),
    path('administrateur/evaluations/creer/', admin_evaluation_create, name='admin_evaluation_create'),
    path('administrateur/evaluations/<int:eval_id>/modifier/', admin_evaluation_edit, name='admin_evaluation_edit'),
    path('administrateur/evaluations/<int:eval_id>/supprimer/', admin_evaluation_delete, name='admin_evaluation_delete'),

    # Ressources
    path('administrateur/ressources/', admin_resources_list, name='admin_resources_list'),
    path('administrateur/ressources/creer/', admin_resource_create, name='admin_resource_create'),
    path('administrateur/ressources/<int:resource_id>/modifier/', admin_resource_edit, name='admin_resource_edit'),
    path('administrateur/ressources/<int:resource_id>/supprimer/', admin_resource_delete, name='admin_resource_delete'),

    # Demandes
    path('administrateur/demandes/', admin_requests_list, name='admin_requests_list'),
    path('administrateur/demandes/<int:req_id>/', admin_request_detail, name='admin_request_detail'),
    path('administrateur/demandes/<int:req_id>/supprimer/', admin_request_delete, name='admin_request_delete'),

    # Notifications
    path('administrateur/notifications/', admin_notifications_list, name='admin_notifications_list'),
    path('administrateur/notifications/creer/', admin_notification_create, name='admin_notification_create'),
    path('administrateur/notifications/<int:notif_id>/supprimer/', admin_notification_delete, name='admin_notification_delete'),

    # Devoirs
    path('administrateur/devoirs/', admin_assignments_list, name='admin_assignments_list'),
    path('administrateur/devoirs/creer/', admin_assignment_create, name='admin_assignment_create'),
    path('administrateur/devoirs/<int:assign_id>/modifier/', admin_assignment_edit, name='admin_assignment_edit'),
    path('administrateur/devoirs/<int:assign_id>/supprimer/', admin_assignment_delete, name='admin_assignment_delete'),

    # Commentaires
    path('administrateur/commentaires/', admin_comments_list, name='admin_comments_list'),
    path('administrateur/commentaires/<int:comment_id>/supprimer/', admin_comment_delete, name='admin_comment_delete'),
]



