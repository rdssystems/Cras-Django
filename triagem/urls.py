from django.urls import path

from . import views

app_name = 'triagem'

urlpatterns = [
    path('registrar/', views.registrar, name='registrar'),
    path('filas/', views.filas, name='filas'),
    path('atender/<int:pk>/', views.atender, name='atender'),
    path('controle/', views.controle, name='controle'),
]
