from django.urls import path

from . import views

app_name = 'tap'

urlpatterns = [
    path('', views.mensal, name='mensal'),
]
