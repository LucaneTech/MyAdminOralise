from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    decorated_view_func = user_passes_test(lambda u: u.is_authenticated and u.role == 'admin', login_url='account_login')(view_func)
    return decorated_view_func

def student_required(view_func):
    decorated_view_func = user_passes_test(lambda u: u.is_authenticated and u.role == 'student', login_url='account_login')(view_func)
    return decorated_view_func

def teacher_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'teacher'):
            messages.error(request, "Accès réservé aux enseignants.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view