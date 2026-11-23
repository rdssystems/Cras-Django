from datetime import date, datetime, time

import openpyxl
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from administrativo.models import RegistroAdministrativo
from atendimentos.models import RegistroAtendimento
from tap.models import TapDiario
from triagem.models import Atendimento


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
    help = 'Importa os dados da planilha PROJETO BANCO DE DADOS - CRAS.xlsx'

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
                motivo=' '.join((texto(linha[i]) for i in range(6, 10) if len(linha) > i and linha[i] is not None)),
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

        wb.close()
        self.stdout.write(self.style.SUCCESS('Importação concluída.'))
