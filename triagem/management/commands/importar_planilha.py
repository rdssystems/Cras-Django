import re
import unicodedata
from datetime import date, datetime, time

import openpyxl
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from administrativo.models import RegistroAdministrativo
from atendimentos.models import RegistroAtendimento
from certidoes.models import Certidao
from dsf.models import Dsf
from tap.models import TapDiario
from triagem.models import Atendimento

ABA_CERTIDOES = 'CERTIDÕES'
ABA_DSF = 'DSF CONCLUÍDO'
DATA_NO_TEXTO = re.compile(r'(\d{1,2})/(\d{1,2})/+(\d{4})')  # aceita o "05/01//2026" digitado na planilha


def primeira_data(texto_livre):
    for dia, mes, ano in DATA_NO_TEXTO.findall(texto_livre):
        try:
            return date(int(ano), int(mes), int(dia))
        except ValueError:
            continue
    return None


def data_e_nota(valor):
    """(data, nota): data da célula ou a primeira achada no texto; nota é o texto, se não for só uma data."""
    if isinstance(valor, (datetime, date)):
        return parse_data(valor), ''
    conteudo = texto(valor)
    if not conteudo:
        return None, ''
    so_data = DATA_NO_TEXTO.fullmatch(conteudo.strip(' *'))
    return primeira_data(conteudo), '' if so_data else conteudo


def texto_ou_data(valor):
    """Células de texto que às vezes trazem uma data (digitada na coluna errada): guarda a data como texto."""
    if isinstance(valor, (datetime, date)):
        return parse_data(valor).strftime('%d/%m/%Y')
    return texto(valor)


def corta(valor, tamanho):
    return valor[:tamanho]


def beneficio_dsf(valor):
    """'CESTA BÁSICA - DSF' -> CESTA BÁSICA; o que não for reconhecido fica como está escrito."""
    chave = unicodedata.normalize('NFKD', valor).encode('ascii', 'ignore').decode().upper()
    for palavra, beneficio in (('CESTA', Dsf.Beneficio.CESTA_BASICA), ('FRALDA', Dsf.Beneficio.FRALDA),
                               ('ABSORVENTE', Dsf.Beneficio.ABSORVENTE)):
        if palavra in chave:
            return beneficio
    return corta(valor, 200)


def texto(valor):
    if valor is None:
        return ''
    if isinstance(valor, float):
        if valor == int(valor):
            return str(int(valor))
        return str(valor)
    return str(valor).strip()


def parse_data(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)) and valor:
        texto = str(int(valor))
        if len(texto) == 8:
            try:
                return date(int(texto[4:8]), int(texto[2:4]), int(texto[0:2]))
            except ValueError:
                return None
    return None


def parse_hora(valor):
    if isinstance(valor, datetime):
        return valor.time()
    # Células só com hora chegam do openpyxl como datetime.time.
    if isinstance(valor, time):
        return valor
    return None


class Command(BaseCommand):
    help = 'Importa a planilha do CRAS (.xlsx): histórico, triagens, atendimentos, TAP, certidões e DSF.'

    def add_arguments(self, parser):
        parser.add_argument('--arquivo', type=str, default=str(settings.BASE_DIR / 'PROJETO BANCO DE DADOS - CRAS.xlsx'))
        parser.add_argument(
            '--forcar', action='store_true',
            help='Importa mesmo que o banco já tenha dados importados (vai DUPLICAR o histórico).',
        )

    def handle(self, *args, **opcoes):
        caminho = opcoes['arquivo']
        ja_importados = RegistroAdministrativo.objects.count()
        if ja_importados and not opcoes['forcar']:
            raise CommandError(
                f'A planilha já foi importada ({ja_importados} registros no histórico administrativo). '
                'Rodar de novo DUPLICA os dados. Se for mesmo isso, use --forcar.'
            )
        wb = openpyxl.load_workbook(caminho, data_only=True, read_only=True)
        try:
            # Tudo ou nada: se uma aba falhar no meio, o banco fica como estava.
            with transaction.atomic():
                self._importar(wb)
        finally:
            wb.close()
        self.stdout.write(self.style.SUCCESS('Importação concluída.'))

    def _importar(self, wb):
        ws = wb['1S2024 ATENDIMENTO ADMINISTRATI']
        registros = []
        for linha in ws.iter_rows(min_row=2, values_only=True):
            nome = texto(linha[0]) if len(linha) > 0 else ''
            if not nome:
                continue
            cpf = texto(linha[2]) if len(linha) > 2 else ''
            bairro = texto(linha[3]) if len(linha) > 3 else ''
            telefone = texto(linha[4]) if len(linha) > 4 else ''
            motivo = texto(linha[6]) if len(linha) > 6 else ''
            servidor = texto(linha[9]).replace('\n', ' / ') if len(linha) > 9 else ''
            registros.append(RegistroAdministrativo(
                nome=nome,
                data_nasc=parse_data(linha[1]) if len(linha) > 1 else None,
                cpf=cpf,
                bairro=bairro,
                telefone=telefone,
                data_atendimento=parse_data(linha[5]) if len(linha) > 5 else None,
                motivo=motivo,
                servidor=servidor,
            ))
        if registros:
            RegistroAdministrativo.objects.bulk_create(registros, batch_size=2000)
        self.stdout.write(self.style.SUCCESS(f'Administrativo (1S2024): {len(registros)} registros importados.'))

        # Linhas sem data são puladas: antes viravam "hoje" e caíam na fila do dia.
        ws = wb['CONTROLE DE ATENDIMENTOS DIÁRIO']
        n = sem_data = 0
        for linha in ws.iter_rows(min_row=3, values_only=True):
            nome = texto(linha[2]) if len(linha) > 2 else ''
            if not nome:
                continue
            data = parse_data(linha[1]) if len(linha) > 1 else None
            if not data:
                sem_data += 1
                continue
            Atendimento.objects.create(
                data=data,
                nome=nome,
                cpf=texto(linha[3]) if len(linha) > 3 else '',
                hora_entrada=parse_hora(linha[4]) if len(linha) > 4 else None,
                hora_atendimento=parse_hora(linha[5]) if len(linha) > 5 else None,
                status=(texto(linha[6]) or 'AGUARDANDO ATENDIMENTO') if len(linha) > 6 else 'AGUARDANDO ATENDIMENTO',
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(
            f'Triagem (controle diário): {n} registros importados, {sem_data} sem data ignorados.'
        ))

        ws = wb['REGISTRO DE ATENDIMENTOS']
        n = ignorados = 0
        for linha in ws.iter_rows(min_row=2, values_only=True):
            if not linha or not any(linha):
                continue
            nome = texto(linha[1]) if len(linha) > 1 else ''
            data = parse_data(linha[0])
            if not nome or not data:
                ignorados += 1
                continue
            RegistroAtendimento.objects.create(
                data=data,
                nome=nome,
                cpf=texto(linha[2]) if len(linha) > 2 else '',
                hora_entrada=parse_hora(linha[3]) if len(linha) > 3 else None,
                hora_atendimento=parse_hora(linha[4]) if len(linha) > 4 else None,
                tipo_atendimento=(texto(linha[5]) or 'OUTRO') if len(linha) > 5 else 'OUTRO',
                # As 4 colunas de motivo viram a mesma lista "; " da múltipla escolha do Atender.
                motivo=RegistroAtendimento.SEPARADOR_MOTIVOS.join(
                    texto(linha[i]) for i in range(6, 10) if len(linha) > i and texto(linha[i])
                ),
                responsavel_legado=texto(linha[10]) if len(linha) > 10 else '',
                observacoes=texto(linha[11]) if len(linha) > 11 else '',
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(
            f'Registro de atendimentos: {n} registros importados, {ignorados} sem nome ou data ignorados.'
        ))

        ws = wb['2026 TAP MENSAL']
        n = 0
        meses = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        for linha in ws.iter_rows(min_row=3, max_row=33, values_only=True):
            for i, mes in enumerate(meses):
                col_dia = i * 2
                col_tap = col_dia + 1
                dia = linha[col_dia] if len(linha) > col_dia else None
                valor = linha[col_tap] if len(linha) > col_tap else None
                if isinstance(dia, (int, float)) and isinstance(valor, (int, float)):
                    TapDiario.objects.update_or_create(
                        data=date(2026, mes, int(dia)), defaults={'tap_diario': int(valor)}
                    )
                    n += 1
        self.stdout.write(self.style.SUCCESS(f'TAP 2026: {n} lançamentos diários importados.'))

        self._importar_certidoes(wb)
        self._importar_dsf(wb)

    def _importar_certidoes(self, wb):
        if ABA_CERTIDOES not in wb.sheetnames:
            self.stdout.write(f'Aba {ABA_CERTIDOES} não encontrada: certidões não importadas.')
            return
        n = ignoradas = 0
        # Linha 1 é o cabeçalho e a linha 2 vem em branco na planilha.
        for linha in wb[ABA_CERTIDOES].iter_rows(min_row=3, values_only=True):
            if not linha or not any(texto(c) for c in linha[:11]):
                continue
            celula = lambda i: linha[i] if len(linha) > i else None  # noqa: E731
            solicitacao, nota_solicitacao = data_e_nota(celula(0))
            if not solicitacao:
                ignoradas += 1
                continue
            recebimento, nota_recebimento = data_e_nota(celula(6))
            entrega, nota_entrega = data_e_nota(celula(9))
            notas = [(rotulo, nota) for rotulo, nota in (
                ('Data da solicitação', nota_solicitacao),
                ('Data do recebimento', nota_recebimento),
                ('Data da entrega', nota_entrega),
            ) if nota]
            Certidao.objects.create(
                data_solicitacao=solicitacao,
                quem_solicitou=corta(texto_ou_data(celula(1)), 200),
                de_quem=corta(texto_ou_data(celula(2)), 200),
                telefone=corta(texto(celula(3)), 30),
                servidor_legado=corta(texto(celula(4)), 200),
                cidade=corta(texto(celula(5)), 100),
                data_recebimento=recebimento,
                nome_contato=corta(texto_ou_data(celula(7)), 200),
                contato_em=corta(texto_ou_data(celula(8)), 200),
                data_entrega=entrega,
                entregue_para=corta(texto_ou_data(celula(10)), 200),
                observacoes='\n'.join(f'{rotulo} (planilha): {nota}' for rotulo, nota in notas),
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(
            f'Certidões: {n} importadas, {ignoradas} sem data de solicitação ignoradas.'
        ))

    def _importar_dsf(self, wb):
        if ABA_DSF not in wb.sheetnames:
            self.stdout.write(f'Aba {ABA_DSF} não encontrada: DSF não importados.')
            return
        n = ignorados = sem_resultado = 0
        # Linha 1 é o título e a linha 2 o cabeçalho.
        for linha in wb[ABA_DSF].iter_rows(min_row=3, values_only=True):
            nome = texto(linha[0]) if linha else ''
            if not nome:
                continue
            data = parse_data(linha[2]) if len(linha) > 2 else None
            if not data:
                ignorados += 1
                continue
            resultado = texto(linha[3]).upper() if len(linha) > 3 else ''
            if resultado not in Dsf.Resultado.values:
                resultado = ''  # sem resultado na planilha: a lista mostra "—" em vez de inventar
                sem_resultado += 1
            Dsf.objects.create(
                nome=corta(nome, 200),
                beneficio_solicitado=beneficio_dsf(texto(linha[1]) if len(linha) > 1 else ''),
                data=data,
                resultado=resultado,
                tecnico_legado=corta(texto(linha[4]), 200) if len(linha) > 4 else '',
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(
            f'DSF: {n} importados ({sem_resultado} sem resultado), {ignorados} sem data ignorados.'
        ))
