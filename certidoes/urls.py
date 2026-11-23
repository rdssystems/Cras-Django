from django.urls import path

from . import views

app_name = 'certidoes'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('nova/', views.criar, name='criar'),
    path('<int:pk>/editar/', views.editar, name='editar'),
]
