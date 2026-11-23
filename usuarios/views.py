from functools import wraps

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import get_object_or_404, redirect, render

from .forms import UsuarioCriarForm, UsuarioEditarForm
from .models import Usuario


def somente_administrador(view):
    @wraps(view)
    @login_required
    def protegida(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, 'Só o administrador do sistema pode gerenciar contas.')
            return redirect('inicio')
        return view(request, *args, **kwargs)
    return protegida


@somente_administrador
def lista(request):
    usuarios = Usuario.objects.order_by('-is_active', 'first_name', 'last_name', 'username')
    return render(request, 'usuarios/lista.html', {'usuarios': usuarios})


@somente_administrador
def criar(request):
    form = UsuarioCriarForm(request.POST or None)
    if form.is_valid():
        usuario = form.save()
        messages.success(request, f'Conta de {usuario} criada. Usuário para entrar: {usuario.username}.')
        return redirect('usuarios:lista')
    return render(request, 'usuarios/form.html', {'form': form, 'titulo': 'Nova conta'})


@somente_administrador
def editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioEditarForm(request.POST or None, instance=usuario, editor=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, f'Conta de {usuario} atualizada.')
        return redirect('usuarios:lista')
    return render(request, 'usuarios/form.html', {'form': form, 'titulo': f'Editar conta de {usuario}', 'usuario': usuario})


@somente_administrador
def senha(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = SetPasswordForm(usuario, request.POST or None)
    for campo in form.fields.values():
        campo.widget.attrs['class'] = 'form-control'
        campo.help_text = ''
    if form.is_valid():
        form.save()
        if usuario.pk == request.user.pk:
            update_session_auth_hash(request, usuario)  # trocar a própria senha não derruba a sessão
        messages.success(request, f'Nova senha de {usuario} definida.')
        return redirect('usuarios:lista')
    return render(request, 'usuarios/senha.html', {'form': form, 'usuario': usuario})


@somente_administrador
def alternar_ativo(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method != 'POST':
        return redirect('usuarios:lista')
    if usuario.pk == request.user.pk:
        messages.error(request, 'Você não pode desativar a sua própria conta.')
        return redirect('usuarios:lista')
    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=['is_active'])
    acao = 'reativada' if usuario.is_active else 'desativada (não consegue mais entrar)'
    messages.success(request, f'Conta de {usuario} {acao}.')
    return redirect('usuarios:lista')
