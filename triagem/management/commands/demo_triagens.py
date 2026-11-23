"""Enche o sistema de triagens fictícias para ver o app lotado (demonstração).

    python manage.py demo_triagens             # apaga a demonstração anterior e cria de novo
    python manage.py demo_triagens --remover   # só apaga a demonstração

Hoje: um dia corrido, com gente na fila em todas as prioridades (a espera é contada a partir de
agora, então rode de novo em outro dia para "hoje" continuar cheio). Dias anteriores: os últimos
30 dias úteis, sem feriados nacionais, com pico de chegada às 8h e um segundo pico às 13h.

Tudo que é de demonstração fica ligado aos servidores fictícios "demo_*" (sem senha: não entram no
sistema). É por eles que o --remover encontra o que apagar, sem tocar nos dados reais.
"""
import random
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from atendimentos.models import RegistroAtendimento
from triagem.models import STATUS_PSICOSSOCIAL, Atendimento
from usuarios.models import Usuario

S = Atendimento.Status
T = RegistroAtendimento.Tipo
C = Usuario.Cargo

PREFIXO = 'demo_'
DIAS = 30
ATENDIDOS_HOJE = 36  # já passaram pela triagem e saíram
NA_FILA_HOJE = 28    # ainda aguardando: é isso que enche as filas
FERIADOS = {(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (11, 20), (12, 25)}

SERVIDORES = {
    'triagem': [('demo_lucia', 'Lúcia', 'Ferreira', C.TECNICO_ADMINISTRATIVO),
                ('demo_rafael', 'Rafael', 'Moura', C.TECNICO_ADMINISTRATIVO)],
    'administrativo': [('demo_carla', 'Carla', 'Nogueira', C.TECNICO_ADMINISTRATIVO),
                       ('demo_joao', 'João', 'Batista', C.TECNICO_ADMINISTRATIVO),
                       ('demo_simone', 'Simone', 'Araújo', C.TECNICO_ADMINISTRATIVO)],
    'psicossocial': [('demo_helena', 'Helena', 'Prado', C.PSICOLOGO),
                     ('demo_marcos', 'Marcos', 'Teixeira', C.ASSISTENTE_SOCIAL)],
}

# Fila em que a pessoa entra na triagem (peso relativo).
FILAS = [
    (S.AGUARDANDO, 40), (S.AGUARDANDO_PSICO, 14), (S.AGUARDANDO_60, 12), (S.AGUARDANDO_PSICO_60, 3),
    (S.AGUARDANDO_80, 3), (S.AGUARDANDO_PSICO_80, 1), (S.AGUARDANDO_GESTANTE, 5),
    (S.AGUARDANDO_PSICO_GESTANTE, 1), (S.AGUARDANDO_PCD, 4), (S.AGUARDANDO_PSICO_PCD, 1),
    (S.AGUARDANDO_AUTISTA, 2), (S.AGUARDANDO_PSICO_AUTISTA, 1),
    (S.LIBRAS, 1), (S.LIBRAS_PSICO, 1), (S.REUNIAO, 1),
]
HORAS_DE_CHEGADA = [(7, 6), (8, 22), (9, 18), (10, 12), (11, 8), (12, 3), (13, 10), (14, 9), (15, 6), (16, 3)]
TRIAGENS_POR_DIA_DA_SEMANA = {0: 62, 1: 50, 2: 48, 3: 46, 4: 38}  # segunda é o dia mais cheio
TIPOS_ADMINISTRATIVOS = [(T.ADMINISTRATIVO, 80), (T.ORIENTACAO, 14), (T.OUTRO, 6)]
MOTIVOS = [
    ('ATUALIZAÇÃO CADASTRAL - CADÚNICO', 40), ('CADASTRO NOVO - CADÚNICO', 18), ('ORIENTAÇÃO', 8),
    ('CESTA BÁSICA', 7), ('DMAE', 6), ('FOLHA RESUMO', 6), ('CERTIDÃO DE NASCIMENTO', 5),
    ('SEGUNDA VIA RG', 4), ('OUTRO', 3), ('CERTIDÃO DE CASAMENTO', 2), ('CERTIDÃO DE ÓBITO', 1),
]

NOMES = [
    'Maria', 'Ana', 'Francisca', 'Antônia', 'Adriana', 'Juliana', 'Márcia', 'Fernanda', 'Patrícia',
    'Aline', 'Sandra', 'Camila', 'Luciana', 'Vanessa', 'Rosângela', 'Cláudia', 'Daniela', 'Jéssica',
    'Josefa', 'Raimunda', 'José', 'João', 'Antônio', 'Francisco', 'Carlos', 'Paulo', 'Pedro', 'Lucas',
    'Luiz', 'Marcos', 'Gabriel', 'Rafael', 'Daniel', 'Marcelo', 'Bruno', 'Eduardo', 'Felipe', 'Raimundo',
    'Sebastião', 'Geraldo', 'Valdete', 'Cleide', 'Edileuza', 'Rogério', 'Wellington', 'Kauã', 'Thaís',
]
SOBRENOMES = [
    'Silva', 'Santos', 'Oliveira', 'Souza', 'Rodrigues', 'Ferreira', 'Alves', 'Pereira', 'Lima', 'Gomes',
    'Costa', 'Ribeiro', 'Martins', 'Carvalho', 'Almeida', 'Lopes', 'Soares', 'Fernandes', 'Vieira',
    'Barbosa', 'Rocha', 'Dias', 'Nascimento', 'Andrade', 'Moreira', 'Nunes', 'Marques', 'Machado',
    'Mendes', 'Freitas', 'Cardoso', 'Ramos', 'Gonçalves', 'Santana', 'Teixeira', 'Pinto', 'Cavalcante',
]


def dias_uteis_anteriores(hoje, quantidade):
    dia = hoje - timedelta(days=quantidade - 1)
    while dia < hoje:
        if dia.weekday() < 5 and (dia.month, dia.day) not in FERIADOS:
            yield dia
        dia += timedelta(days=1)


def demo_queryset():
    """Triagens e registros de demonstração (e só eles)."""
    servidores = Usuario.objects.filter(username__startswith=PREFIXO)
    triagens = Atendimento.objects.filter(servidor_triagem__in=servidores)
    registros = RegistroAtendimento.objects.filter(
        Q(atendimento_origem__in=triagens) | Q(responsavel__in=servidores)
    )
    return servidores, triagens, registros


class Command(BaseCommand):
    help = 'Cria (ou com --remover, apaga) triagens fictícias para ver o app lotado.'

    def add_arguments(self, parser):
        parser.add_argument('--remover', action='store_true', help='Só apaga a demonstração.')
        parser.add_argument('--semente', type=int, default=2026, help='Semente do sorteio (mesma semente, mesmos dados).')

    @transaction.atomic
    def handle(self, *args, **opcoes):
        removidos = self.remover()
        if opcoes['remover']:
            self.stdout.write(self.style.SUCCESS(
                'Demonstração removida: {} triagens, {} registros de atendimento, {} servidores fictícios.'
                .format(*removidos)
            ))
            return

        self.rng = random.Random(opcoes['semente'])
        self.criar_servidores()
        self.triagens, self.registros = [], []

        agora = timezone.localtime().replace(tzinfo=None)
        for dia in dias_uteis_anteriores(agora.date(), DIAS):
            self.dia_anterior(dia)
        self.hoje(agora)

        # O bulk_create preenche a pk das triagens; o Django leva essa pk para atendimento_origem.
        Atendimento.objects.bulk_create(self.triagens, batch_size=500)
        RegistroAtendimento.objects.bulk_create(self.registros, batch_size=500)

        na_fila = sum(1 for t in self.triagens if t.data == agora.date() and t.status not in (S.ATENDIDO, S.ATENDIDO_TRIAGEM))
        self.stdout.write(self.style.SUCCESS(
            f'Demonstração criada: {len(self.triagens)} triagens ({na_fila} aguardando hoje) e '
            f'{len(self.registros)} registros de atendimento.\n'
            'Para apagar: python manage.py demo_triagens --remover'
        ))

    # ------------------------------------------------------------ servidores e sorteios

    def remover(self):
        servidores, triagens, registros = demo_queryset()
        n_registros = registros.delete()[0]
        n_triagens = triagens.delete()[0]
        n_servidores = servidores.delete()[0]
        return n_triagens, n_registros, n_servidores

    def criar_servidores(self):
        self.servidores = {}
        for grupo, pessoas in SERVIDORES.items():
            self.servidores[grupo] = []
            for username, nome, sobrenome, cargo in pessoas:
                usuario = Usuario(username=username, first_name=nome, last_name=sobrenome, cargo=cargo)
                usuario.set_unusable_password()
                usuario.save()
                self.servidores[grupo].append(usuario)

    def sortear(self, pesos):
        opcoes, pesos = zip(*pesos)
        return self.rng.choices(opcoes, weights=pesos)[0]

    def nome(self):
        sobrenomes = self.rng.sample(SOBRENOMES, 2)
        return f'{self.rng.choice(NOMES)} {" ".join(sobrenomes)}'.upper()

    def cpf(self):
        """CPF com dígito verificador propositalmente errado: nunca coincide com o de alguém real."""
        if self.rng.random() < 0.15:
            return ''  # chegou sem documento
        digitos = [self.rng.randint(0, 9) for _ in range(9)]
        for _ in range(2):
            soma = sum(d * p for d, p in zip(digitos, range(len(digitos) + 1, 1, -1)))
            digitos.append(soma * 10 % 11 % 10)
        digitos[9] = (digitos[9] + 1) % 10
        texto = ''.join(map(str, digitos))
        return f'{texto[:3]}.{texto[3:6]}.{texto[6:9]}-{texto[9:]}'

    # ------------------------------------------------------------ dias

    def proximo_numero(self, dia):
        ultimo = Atendimento.objects.filter(data=dia).aggregate(m=Max('numero'))['m'] or 0
        return ultimo + 1

    def chegada_num_dia_util(self, dia):
        hora = self.sortear(HORAS_DE_CHEGADA)
        return datetime.combine(dia, time(hora, self.rng.randint(0, 59)))

    def dia_anterior(self, dia):
        quantidade = round(TRIAGENS_POR_DIA_DA_SEMANA[dia.weekday()] * self.rng.uniform(0.8, 1.2))
        chegadas = sorted(self.chegada_num_dia_util(dia) for _ in range(quantidade))
        numero = self.proximo_numero(dia)
        for entrada in chegadas:
            sorteio = self.rng.random()
            desfecho = 'atendido' if sorteio < 0.72 else 'triagem' if sorteio < 0.90 else 'foi_embora'
            # De manhã a fila é maior, então a espera também.
            espera = self.rng.randint(8, 50) + (25 if entrada.hour < 11 else 0)
            self.adicionar(entrada, numero, desfecho, espera)
            numero += 1

    def sortear_horario(self, inicio, fim):
        segundos = max((fim - inicio).total_seconds(), 60)
        return inicio + timedelta(seconds=self.rng.random() * segundos)

    def hoje(self, agora):
        """Um dia corrido até agora: quem chegou cedo já foi atendido; a fila atual chegou na última hora e meia."""
        meia_noite = datetime.combine(agora.date(), time(0, 1))
        inicio = max(agora - timedelta(hours=5), meia_noite)
        inicio_fila = max(agora - timedelta(minutes=100), meia_noite)

        chegadas = []
        for _ in range(ATENDIDOS_HOJE):
            entrada = self.sortear_horario(inicio, agora - timedelta(minutes=30))
            chegadas.append((entrada, 'atendido' if self.rng.random() < 0.82 else 'triagem'))
        for _ in range(NA_FILA_HOJE):
            chegadas.append((self.sortear_horario(inicio_fila, agora - timedelta(minutes=2)), 'aguardando'))

        numero = self.proximo_numero(agora.date())
        for entrada, desfecho in sorted(chegadas):
            minutos = int((agora - entrada).total_seconds() // 60)
            espera = self.rng.randint(5, max(5, min(minutos - 1, 70)))
            self.adicionar(entrada, numero, desfecho, espera)
            numero += 1

    def adicionar(self, entrada, numero, desfecho, espera):
        fila = self.sortear(FILAS)
        triagem = Atendimento(
            numero=numero, data=entrada.date(), nome=self.nome(), cpf=self.cpf(),
            hora_entrada=entrada.time().replace(second=0, microsecond=0),
            status=fila, servidor_triagem=self.rng.choice(self.servidores['triagem']),
        )
        self.triagens.append(triagem)
        if desfecho == 'triagem':
            triagem.status = S.ATENDIDO_TRIAGEM
        elif desfecho == 'atendido':
            self.atender(triagem, fila, entrada, espera)

    def atender(self, triagem, fila, entrada, espera):
        atendido_em = min(entrada + timedelta(minutes=espera),
                          datetime.combine(entrada.date(), time(23, 59)))
        psicossocial = fila in STATUS_PSICOSSOCIAL
        if psicossocial:
            tipo, motivo = T.PSICOSSOCIAL, 'PSICOSSOCIAL'
            servidor = self.rng.choice(self.servidores['psicossocial'])
        else:
            tipo = self.sortear(TIPOS_ADMINISTRATIVOS)
            if tipo == T.ORIENTACAO:
                motivo = 'ORIENTAÇÃO'
            else:
                # Um em cada cinco resolve mais de uma coisa no mesmo atendimento.
                quantos = 2 if self.rng.random() < 0.2 else 1
                motivo = RegistroAtendimento.juntar_motivos(self.sortear(MOTIVOS) for _ in range(quantos))
            servidor = self.rng.choice(self.servidores['administrativo'])

        triagem.status = S.ATENDIDO
        triagem.hora_atendimento = atendido_em.time().replace(second=0, microsecond=0)
        triagem.servidor1 = servidor
        self.registros.append(RegistroAtendimento(
            data=triagem.data, nome=triagem.nome, cpf=triagem.cpf,
            hora_entrada=triagem.hora_entrada, hora_atendimento=triagem.hora_atendimento,
            tipo_atendimento=tipo, motivo=motivo, responsavel=servidor, atendimento_origem=triagem,
        ))
