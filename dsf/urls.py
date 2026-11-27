from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'dsf'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('novo/', views.criar, name='criar'),
    path('<int:pk>/editar/', views.editar, name='editar'),
    # Endereços que estas páginas tiveram antes de virarem apps próprios (ficam no histórico do navegador).
    path('isencao-dmae/', RedirectView.as_view(pattern_name='dmae:lista')),
    path('pro-pao/', RedirectView.as_view(pattern_name='propao:lista')),
]
