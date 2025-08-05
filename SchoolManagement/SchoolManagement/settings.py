from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!

# SECURITY WARNING: don't run with debug turned on in production!
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS =[ "http://127.0.0.1:8000","https://oralise.up.railway.app"]


import os

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# STATIC_URL = '/static/'

# STATICFILES_DIRS = [
#     os.path.join(BASE_DIR, 'static')
# ]






# Application definition

INSTALLED_APPS = [
    #customise django-admin with django-jazzmin
    'jazzmin',
    # Default django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    #extensions
    'django_extensions',

    
 
   
    # Dashboard app
    'dashboard',
    'widget_tweaks',

    #for django-allauth
   
    'django.contrib.sites',
     'allauth',
    'allauth.account',
    'allauth.socialaccount',
    
    #social account
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.google',
    
    #django-compressor to compress css and js files
    'compressor',
    
]

#djang-compressor
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]
COMPRESS_ENABLED = True
COMPRESS_OFFLINE = False  

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')] 
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')   
COMPRESS_ROOT = STATIC_ROOT
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'





# django-allauth settings
AUTHENTICATION_BACKENDS = [
   
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Default primary key field type about django-allauth settings
SITE_ID = 8

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # django-allauth middleware
    'allauth.account.middleware.AccountMiddleware',
]
# Configuration de l'authentification via les réseaux sociaux

SOCIALACCOUNT_PROVIDERS = {
    
    'github': {
         'APP':{
            'client_id':config('GITHUB_ID'),
            'secret': config('GITHUB_SECRET'),
            'key':''
                 
         }
      
    },
      'google': {
        'APP': {
            'client_id': config('GOOGLE_ID'),
            'secret': config('GOOGLE_SECRET'),
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
    
    # 'facebook': {
    #     'APP': {
    #         'client_id': '1333999141190521', 
    #         'secret': '76476daf43f4274a9af88536aa3fe53e',  
    #     },
    #     'AUTH_PARAMS':{
    #         'auth_type':'reauthenticate',
    #     },
        # 'SCOPE': ['email', 'public_profile'],
        # 'AUTH_PARAMS': {'auth_type': 'reauthenticate'},            
        # 'OAUTH_PKCE_ENABLED': True,
        # 'FIELDS': ['id', 'email', 'name', 'first_name', 'last_name'], 
        # 'EXCHANGE_TOKEN': True,
        # 'METHOD': 'oauth2', 
        # 'VERIFIED_EMAIL': False,
        # 'VERSION': 'v18.0',

        
 #   }
}

SOCIAL_AUTH_REDIRECT_IS_HTTPS = True  # Important si tu utilises ngrok avec HTTPS
# SOCIAL_AUTH_LOGIN_REDIRECT_URL = 'home'
SOCIAL_AUTH_NEW_USER_REDIRECT_URL = 'dashboard_home'
SOCIAL_AUTH_LOGIN_ERROR_URL = 'dashboard_home'
# SOCIAL_AUTH_USER_MODEL = 'dashboard.CustomUser'
# SOCIAL_AUTH_FACEBOOK_AUTH_EXTRA_ARGUMENTS = {'auth_type': 'reauthenticate'}
SOCIALACCOUNT_LOGIN_ON_GET=True
SOCIALACCOUNT_QUERY_EMAIL = True

#redirection url after login
LOGIN_REDIRECT_URL = 'dashboard_home'
#redirection url after logout
LOGOUT_REDIRECT_URL = 'account_login'

# django-allauth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_EMAIL_VERIFICATION = 'none'  # Temporairement désactivé pour le développement

ROOT_URLCONF = 'SchoolManagement.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'SchoolManagement.settings.current_year', 
            ],
        },
    },
]




WSGI_APPLICATION = 'SchoolManagement.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

#DATABASES = {
    #'default': {
        #'ENGINE': 'django.db.backends.sqlite3',
       # 'NAME': BASE_DIR / 'db.sqlite3',
    #}
#}

DATABASES ={
    'default':{
        'ENGINE':'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD':config('DB_PASSWORD'),
        'HOST':config('DB_HOST'),
        'PORT':config('DB_PORT')
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'fr-fr'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True




DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



# django allauth include customforms of form.py
ACCOUNT_FORMS = {
     'login': 'dashboard.forms.CustomLoginForm',
     'signup': 'dashboard.forms.CustomSignupForm',
     'password_reset': 'dashboard.forms.CustomResetPasswordForm',
}
#Customise of user's role login
AUTH_USER_MODEL = 'dashboard.CustomUser'

#Apply email reception in console
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

#configure of email backend

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Pour le développement



# Configuration pour django-allauth
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_EMAIL_VERIFICATION = 'none'  # Temporairement désactivé pour le développement


#django-jazzmin settings for admin dashboard
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": True,
    "brand_small_text": False,
    "brand_colour": "navbar-success",
    "accent": "accent-success",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-success",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": True,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
    "actions_sticky_top": True,
    "language_chooser": True
}

#all about django-jazz for admin dashboard
JAZZMIN_SETTINGS = {
    
    #navbar admin-dashboard
       "topmenu_links": [
        {"name": "Home", "url": "home", "permissions": ["auth.view_user"]},
    ],
       
    
    "site_title": "Oralise",
    "site_header": "Administration Oralise",
    "site_brand": "ORALISE",
     "site_logo":None,
    "login_logo": "public/img/logo.png",
    #favicon
       "site_icon": "public/img/favic.png",
       
    "icons": {
        # Authentification
        "auth": "fas fa-user-shield",
        "auth.group": "fas fa-users-cog",
        "auth.user": "fas fa-user",

        # by using django-allauth
        "account": "fas fa-user-circle",
        "account.emailaddress": "fas fa-envelope",
        "socialaccount": "fas fa-share-alt",
        "socialaccount.socialapp": "fas fa-thumbs-up",
        "socialaccount.socialaccount": "fas fa-user-friends",
        "socialaccount.socialtoken": "fas fa-key",

        # Edusco app
        "edusco": "fas fa-school",

        # Modèles personnalisés
        "dashboard.customuser": "fas fa-user-cog",         # CustomUser
        "dashboard.student": "fas fa-user-graduate",       # Student
        "dashboard.teacher": "fas fa-chalkboard-teacher",  # Teacher
        "dashboard.skill": "fas fa-lightbulb",             # Skill
        "dashboard.schedule": "fas fa-calendar-alt",       # Schedule
        "dashboard.mark": "fas fa-star",                   # Mark
        "dashboard.language": "fas fa-language",           # Language
        "dashboard.session": "fas fa-clock",               # Session
        "dashboard.payment": "fas fa-money-bill",          # Payment
        "dashboard.certificate": "fas fa-certificate",     # Certificate
        "dashboard.evaluation": "fas fa-chart-line",       # Evaluation
        "dashboard.notification": "fas fa-bell",           # Notification

        # Sites
        "sites": "fas fa-globe",
        "sites.site": "fas fa-map-marker-alt",
    },
    
    "welcome_sign": "Bienvenue dans Oralise",
    "copyright": "Oralise",
    "user_avatar": None,
    
    #this concern models applying like popup
     "related_modal_active":False,

     #this code concern admin-dashboard style
     #"show_ui_builder": True,
    

}

#admin dashboard style making tanks to show_ui_builder

#current year
from datetime import datetime
def current_year(request):
    return {'current_year': datetime.now().year}



