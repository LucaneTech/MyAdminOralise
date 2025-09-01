from django import template
from django.template.defaultfilters import floatformat

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Récupère un élément d'un dictionnaire par sa clé"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def get_nested_item(dictionary, keys):
    """Récupère un élément imbriqué d'un dictionnaire par une liste de clés"""
    if dictionary is None:
        return None
    
    current = dictionary
    for key in keys.split('.'):
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current

@register.filter
def multiply(value, arg):
    """Multiplie une valeur par un argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_attendance_status(student_id, attendance_dict):
    """Récupère le statut de présence d'un étudiant"""
    if attendance_dict and student_id in attendance_dict:
        return attendance_dict[student_id].status
    return 'present'

@register.filter
def get_attendance_arrival_time(student_id, attendance_dict):
    """Récupère l'heure d'arrivée d'un étudiant"""
    if attendance_dict and student_id in attendance_dict:
        return attendance_dict[student_id].arrival_time
    return None

@register.filter
def get_attendance_note(student_id, attendance_dict):
    """Récupère la note de présence d'un étudiant"""
    if attendance_dict and student_id in attendance_dict:
        return attendance_dict[student_id].note
    return ''

@register.filter
def format_duration(minutes):
    """Formate une durée en minutes en format lisible"""
    if minutes is None:
        return "0 min"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours > 0:
        if remaining_minutes > 0:
            return f"{hours}h {remaining_minutes}min"
        else:
            return f"{hours}h"
    else:
        return f"{remaining_minutes}min"

@register.filter
def get_attendance_status_class(status):
    """Retourne la classe CSS pour le statut de présence"""
    status_classes = {
        'present': 'status-present',
        'absent': 'status-absent',
        'late': 'status-late',
        'excused': 'status-excused'
    }
    return status_classes.get(status, 'status-default')

@register.filter
def get_session_status_color(status):
    """Retourne la classe CSS pour le statut d'une séance"""
    status_colors = {
        'scheduled': 'primary',
        'completed': 'success',
        'cancelled': 'danger',
        'rescheduled': 'warning',
        'absent': 'secondary'
    }
    return status_colors.get(status, 'secondary')

@register.filter
def get_evaluation_score_color(score):
    """Retourne la classe CSS pour la note d'une évaluation"""
    try:
        score = float(score)
        if score >= 16:
            return 'success'
        elif score >= 12:
            return 'warning'
        else:
            return 'danger'
    except (ValueError, TypeError):
        return 'secondary'

@register.filter
def truncate_words(text, length=20):
    """Tronque un texte à un nombre de mots donné"""
    if not text:
        return ""
    
    words = text.split()
    if len(words) <= length:
        return text
    
    return " ".join(words[:length]) + "..."

@register.filter
def get_resource_type_icon(resource_type):
    """Retourne l'icône appropriée pour le type de ressource"""
    icons = {
        'document': 'fas fa-file-alt',
        'link': 'fas fa-link',
        'video': 'fas fa-video',
        'other': 'fas fa-file'
    }
    return icons.get(resource_type, 'fas fa-file')

@register.filter
def get_language_code(language):
    """Retourne le code de langue pour les filtres"""
    if hasattr(language, 'code'):
        return language.code
    return str(language)

@register.filter
def get_skill_name(skill):
    """Retourne le nom de la matière"""
    if hasattr(skill, 'name'):
        return skill.name
    return str(skill)

@register.filter
def get_student_name(student):
    """Retourne le nom complet de l'étudiant"""
    if hasattr(student, 'user') and hasattr(student.user, 'get_full_name'):
        return student.user.get_full_name()
    return str(student)

@register.filter
def get_teacher_name(teacher):
    """Retourne le nom complet de l'enseignant"""
    if hasattr(teacher, 'user') and hasattr(teacher.user, 'get_full_name'):
        return teacher.user.get_full_name()
    return str(teacher)

@register.filter
def format_datetime(datetime_obj, format_str="d/m/Y H:i"):
    """Formate une date/heure"""
    if not datetime_obj:
        return ""
    
    try:
        return datetime_obj.strftime(format_str)
    except AttributeError:
        return str(datetime_obj)

@register.filter
def format_time(time_obj, format_str="H:i"):
    """Formate une heure"""
    if not time_obj:
        return ""
    
    try:
        return time_obj.strftime(format_str)
    except AttributeError:
        return str(time_obj)

@register.filter
def format_date(date_obj, format_str="d/m/Y"):
    """Formate une date"""
    if not date_obj:
        return ""
    
    try:
        return date_obj.strftime(format_str)
    except AttributeError:
        return str(date_obj)

@register.filter
def get_language_color_class(language_name):
    """Retourne la classe CSS pour la couleur de la langue"""
    language_colors = {
        'Français': 'course-french',
        'Anglais': 'course-english',
        'Espagnol': 'course-spanish',
        'Allemand': 'course-german',
        'Italien': 'course-italian',
        'Chinois': 'course-chinese',
        'Japonais': 'course-japanese',
        'Arabe': 'course-arabic',
    }
    return language_colors.get(language_name, 'course-default')

# Force reload des filtres - Django 5.1.6
register.filters['get_item'] = get_item 