from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('nova/', views.criar, name='criar'),
    path('<int:pk>/editar/', views.editar, name='editar'),
    path('<int:pk>/senha/', views.senha, name='senha'),
    path('<int:pk>/ativar/', views.alternar_ativo, name='alternar_ativo'),
]
