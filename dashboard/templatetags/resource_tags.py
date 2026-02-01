# dashboard/templatetags/resource_tags.py
from django import template
from django.utils import timezone
from django.utils.html import format_html

register = template.Library()

@register.filter
def resource_badge(resource_type):
    """Retourne un badge coloré selon le type de ressource"""
    badges = {
        'document': 'primary',
        'video': 'danger',
        'link': 'success',
        'other': 'warning',
    }
    color = badges.get(resource_type, 'secondary')
    return format_html('<span class="badge badge-{}">{}</span>', color, resource_type)

@register.filter
def language_badges(languages):
    """Retourne les badges de langues"""
    badges = []
    for language in languages:
        color = language.color if hasattr(language, 'color') else 'info'
        badges.append(
            format_html('<span class="badge badge-{} mr-1">{}</span>', color, language.name)
        )
    return format_html(''.join(badges))

@register.filter
def is_new(resource_date, days=3):
    """Vérifie si une ressource est nouvelle"""
    return resource_date >= timezone.now() - timezone.timedelta(days=days)

@register.filter
def resource_actions(resource):
    """Retourne les boutons d'action pour une ressource"""
    actions = []
    if resource.file:
        actions.append(
            format_html(
                '<a href="{}" class="btn btn-sm btn-primary mr-1" target="_blank" download>'
                '<i class="ni ni-cloud-download-95"></i> Télécharger</a>',
                resource.file.url
            )
        )
    if resource.url:
        actions.append(
            format_html(
                '<a href="{}" class="btn btn-sm btn-info" target="_blank" rel="noopener noreferrer">'
                '<i class="ni ni-world-2"></i> Accéder</a>',
                resource.url
            )
        )
    return format_html(''.join(actions))

@register.simple_tag
def resource_icon(resource_type):
    """Retourne l'icône appropriée pour le type de ressource"""
    icons = {
        'document': 'ni ni-single-copy-04',
        'video': 'ni ni-video-camera',
        'link': 'ni ni-world-2',
        'other': 'ni ni-collection',
    }
    return icons.get(resource_type, 'ni ni-collection')