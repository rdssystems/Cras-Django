from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from cras import views as cras_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', cras_views.inicio, name='inicio'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('triagem/', include('triagem.urls')),
    path('atendimentos/', include('atendimentos.urls')),
    path('certidoes/', include('certidoes.urls')),
    path('dsf/', include('dsf.urls')),
    path('isencao-dmae/', include('dmae.urls')),
    path('pro-pao/', include('propao.urls')),
    path('tap/', include('tap.urls')),
    path('usuarios/', include('usuarios.urls')),
]
