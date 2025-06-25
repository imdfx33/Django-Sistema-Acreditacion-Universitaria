
"""
URL configuration for todo_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.contrib import admin

from django.shortcuts import redirect
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from login.views import login_view

urlpatterns = [
    #login
    path('', lambda request: redirect('login')),
    path('login/', include('login.urls')),
    
    # Admin
    path('admin/', admin.site.urls),


    path('home/', include('home.urls')),

    path('formularios/', include('formularios.urls')),

    path('attachGeneric/', include('attachGeneric.urls')),

    path('createEvent/', include('calendar_create_event.urls')), 

    path('reuniones/', include('meeting_List.urls')),

    path('assignments/', include('assignments.urls')),

    path('', include('strategicAnalysis.urls')),
    
    #para reports:
    path('reports/', include('reports.urls', namespace='reports')),
    


]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)    
