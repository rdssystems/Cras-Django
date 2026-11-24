from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from .models import RegistroAdministrativo


@login_required
def lista(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    registros = RegistroAdministrativo.objects.all()
    q = request.GET.get('q', '').strip()
    if q:
        registros = (
            registros.filter(nome__icontains=q)
            | registros.filter(cpf__icontains=q)
            | registros.filter(motivo__icontains=q)
        )
    paginator = Paginator(registros, 50)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'administrativo/lista.html', {'page': page, 'q': q})
