from django.contrib import admin
from django.urls import path,include

#upload profil_pic about profil creation
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    #admin urls
    path('admin/', admin.site.urls),
    
    #django-allauth urls
    path('accounts/', include('allauth.urls')), 
    
    #include dashboard urls
    path('', include('dashboard.urls')),

        
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

