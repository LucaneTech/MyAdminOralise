from pathlib import Path
import dj_database_url
from dotenv import load_dotenv
import os
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent



# SECURITY WARNING: don't run with debug turned on in production!
load_dotenv()
SECRET_KEY = os.environ.get("SECRET_KEY")
DEBUG = os.environ.get("DEBUG")


ALLOWED_HOSTS = [
    "oraliseadmin.up.railway.app",
    "127.0.0.1",
    "localhost",
]

CSRF_TRUSTED_ORIGINS = [
    "https://oraliseadmin.up.railway.app",
    "http://127.0.0.1:8000",
]






# MEDIA_URL = '/media/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# AWS S3 / Railway Bucket
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL")
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME")

AWS_QUERYSTRING_AUTH = os.environ.get("AWS_QUERYSTRING_AUTH")
AWS_DEFAULT_ACL = os.environ.get("AWS_DEFAULT_ACL")

# Utiliser S3 pour tous les fichiers médias
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# MEDIA_URL n'est plus locale, elle pointe vers le bucket
MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"


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

    #bucket of railway
    'storages',
    
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
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'static/assets'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')   
COMPRESS_ROOT = STATIC_ROOT

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"


AUTHENTICATION_BACKENDS = [
   
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]


# SITE_ID = 1
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

SOCIALACCOUNT_PROVIDERS = {
    
    # 'github': {
    #      'APP':{
    #         'client_id':os.environ.get('GITHUB_ID'),
    #         'secret': os.environ.get('GITHUB_SECRET'),
    #         'key':''
                 
    #      }
      
    # },
    #   'google': {
    #     'APP': {
    #         'client_id': os.environ.get('GOOGLE_ID'),
    #         'secret': os.environ.get('GOOGLE_SECRET'),
    #         'key': ''
    #     },
    #     'SCOPE': [
    #         'profile',
    #         'email',
    #     ],
    #     'AUTH_PARAMS': {
    #         'access_type': 'online',
    #     },
    #     'OAUTH_PKCE_ENABLED': True,
    # }
    
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

SOCIAL_AUTH_REDIRECT_IS_HTTPS = False 
SOCIAL_AUTH_LOGIN_REDIRECT_URL = 'dashboard_home'
SOCIAL_AUTH_NEW_USER_REDIRECT_URL = 'dashboard_home'
SOCIAL_AUTH_LOGIN_ERROR_URL = 'dashboard_home'
# SOCIAL_AUTH_USER_MODEL = 'dashboard.CustomUser'

SOCIALACCOUNT_LOGIN_ON_GET=True
SOCIALACCOUNT_QUERY_EMAIL = True



# if not DEBUG:
#     SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", True)
#     SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", True)
#     CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", True)



#redirection url after login
LOGIN_REDIRECT_URL = 'dashboard_home'

#redirection url after logout
LOGOUT_REDIRECT_URL = 'account_login'

# django-allauth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_EMAIL_VERIFICATION = 'none' 

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

if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.parse(
            os.environ.get("DATABASE_URL"),
            conn_max_age=600,
            ssl_require=True
        )
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

LANGUAGE_CODE = 'fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_L10N = True
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


#os.environ.geture of email backend

# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'profrancisco579@gmail.com'
# EMAIL_HOST_PASSWORD ='gouawphttulrhwan'
# DEFAULT_FROM_EMAIL = 'profrancisco579@gmail.com'




#django-jazzmin settings for admin dashboard
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": True,
    "brand_small_text": True,
    "brand_colour": "navbar-cyan",
    "accent": "accent-lightblue",
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": True,
    "sidebar_nav_flat_style": False,
    "theme": "flatly",
    "dark_mode_theme": "cyborg",
    "button_classes": {
        "primary": "btn-outline-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
    "actions_sticky_top": True,
    "language_chooser": True,
    "custom_css": "assets/css/jazzmin.css",
    "login_logo_classes": "custom-logo"
}

#all about django-jazz for admin dashboard
JAZZMIN_SETTINGS = {
    
    #navbar admin-dashboard
       "topmenu_links": [
        {"name": "Home", "url": "home", "permissions": ["auth.view_user"]},
    ],
       
    
    "site_title": "Oralise",
    "site_header": "Admin Oralise",
    "site_brand": "ORALISE",
     "site_logo":None,
    "login_logo": "",
    

    #favicon
       "site_icon": "",
       
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
        "dashboard.ressource": "fas fa-inbox",              # Request
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
     "show_ui_builder": False,
    

}




EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 465))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = 'Oralise <contact@oralise.pro>'





#current year
from datetime import datetime
def current_year(request):
    return {'current_year': datetime.now().year}



