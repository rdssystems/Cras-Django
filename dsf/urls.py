from django.urls import path

from . import views

app_name = 'dsf'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('novo/', views.criar, name='criar'),
]
