from django import template

register = template.Library()

@register.filter
def get(dictionary, key):
    return dictionary.get(key)

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(list_or_dict, index_or_key):
    """
    Filtre pour accéder aux éléments d'une liste ou d'un dictionnaire dans les templates.
    Utilisé pour les graphiques dynamiques.
    """
    try:
        if isinstance(list_or_dict, (list, tuple)):
            return list_or_dict[int(index_or_key)]
        elif isinstance(list_or_dict, dict):
            return list_or_dict.get(index_or_key)
        return None
    except (IndexError, KeyError, ValueError, TypeError):
        return None 