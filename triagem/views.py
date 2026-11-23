from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from atendimentos.models import RegistroAtendimento

from .forms import AtendimentoForm
from .models import STATUS_FILA, Atendimento, TipoFila, listas_de_chamada, pode_atender


@login_required
def registrar(request):
    if request.method == 'POST':
        form = AtendimentoForm(request.POST)
        if form.is_valid():
            atendimento = form.save(commit=False)
            atendimento.servidor_triagem = request.user
            atendimento.save()
            if atendimento.status in STATUS_FILA:
                fila = TipoFila(form.cleaned_data['tipo_fila']).label.lower()
                prioridade = f' ({atendimento.etiqueta})' if atendimento.etiqueta else ''
                messages.success(request, f'Senha Nº {atendimento.numero}: {atendimento.nome} entrou na fila de {fila}{prioridade}.')
            else:
                messages.success(request, f'{atendimento.nome} registrado(a) como resolvido(a) na triagem.')
            return redirect('triagem:registrar')
    else:
        form = AtendimentoForm()
    return render(request, 'triagem/registrar.html', {'form': form})


@login_required
def filas(request):
    hoje = timezone.localdate()
    listas = listas_de_chamada(hoje)
    for lista in listas:
        # No "Atender", o tipo já vem marcado conforme a fila de onde a pessoa foi chamada.
        tipo_padrao = (RegistroAtendimento.Tipo.PSICOSSOCIAL if lista['chave'] == 'psicossocial'
                       else RegistroAtendimento.Tipo.ADMINISTRATIVO)
        for item in lista['itens']:
            item.pode = pode_atender(request.user, item.status)
            item.tipo_padrao = tipo_padrao
        lista['sem_permissao'] = bool(lista['itens']) and not any(i.pode for i in lista['itens'])
    return render(request, 'triagem/filas.html', {
        'listas': listas, 'hoje': hoje,
        'tipos_atendimento': RegistroAtendimento.Tipo.choices,
        'motivos': RegistroAtendimento.MOTIVOS,
    })


@login_required
def atender(request, pk):
    if request.method != 'POST':
        return redirect('triagem:filas')
    atendimento = get_object_or_404(Atendimento.objects.select_related('servidor1'), pk=pk)

    if atendimento.status not in STATUS_FILA:
        quem = f' por {atendimento.servidor1}' if atendimento.servidor1_id else ''
        messages.warning(request, f'{atendimento.nome} já foi atendido(a){quem}.')
        return redirect('triagem:filas')

    if not pode_atender(request.user, atendimento.status):
        messages.error(request, 'Seu cargo não pode atender esta fila.')
        return redirect('triagem:filas')

    tipo = request.POST.get('tipo_atendimento', '')
    if tipo not in RegistroAtendimento.Tipo.values:
        tipo = RegistroAtendimento.Tipo.ADMINISTRATIVO

    agora = timezone.localtime()
    with transaction.atomic():
        # UPDATE condicional: só um servidor consegue tirar a pessoa da fila.
        # Duplo clique, F5 ou dois servidores ao mesmo tempo -> o segundo atualiza 0 linhas.
        tirou_da_fila = Atendimento.objects.filter(pk=pk, status=atendimento.status).update(
            status=Atendimento.Status.ATENDIDO,
            hora_atendimento=agora.time(),
            servidor1=request.user,
        )
        if not tirou_da_fila:
            messages.warning(request, f'{atendimento.nome} acabou de ser atendido(a) por outro servidor.')
            return redirect('triagem:filas')

        RegistroAtendimento.objects.create(
            data=agora.date(),
            nome=atendimento.nome,
            cpf=atendimento.cpf,
            hora_entrada=atendimento.hora_entrada,
            hora_atendimento=agora.time(),
            tipo_atendimento=tipo,
            motivo=RegistroAtendimento.juntar_motivos(request.POST.getlist('motivo')),
            responsavel=request.user,
            observacoes=request.POST.get('observacoes', ''),
            atendimento_origem=atendimento,
        )

    messages.success(request, f'{atendimento.nome} atendido(a) por {request.user}.')
    return redirect('triagem:filas')


@login_required
def controle(request):
    data = request.GET.get('data')
    try:
        dia = date.fromisoformat(data) if data else timezone.localdate()
    except ValueError:
        dia = timezone.localdate()
    atendimentos = Atendimento.objects.filter(data=dia)
    total = atendimentos.count()
    atendidos = atendimentos.filter(status=Atendimento.Status.ATENDIDO).count()
    aguardando = atendimentos.filter(status__in=STATUS_FILA).count()
    return render(request, 'triagem/controle.html', {
        'atendimentos': atendimentos,
        'dia': dia,
        'total': total,
        'atendidos': atendidos,
        'aguardando': aguardando,
    })
