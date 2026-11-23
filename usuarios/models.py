from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Cargo(models.TextChoices):
        ASSISTENTE_SOCIAL = 'ASSISTENTE_SOCIAL', 'Assistente Social'
        PSICOLOGO = 'PSICOLOGO', 'Psicólogo(a)'
        # O valor guardado continua TECNICO_ADMINISTRATIVO (contas já existentes); na tela é "Administrativo".
        TECNICO_ADMINISTRATIVO = 'TECNICO_ADMINISTRATIVO', 'Administrativo'

    cargo = models.CharField('Cargo', max_length=30, choices=Cargo.choices, blank=True, null=True)

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def nome_display(self):
        return str(self)

    @property
    def cargo_exibicao(self):
        if self.cargo:
            return self.get_cargo_display()
        return 'Administrador' if self.is_superuser else 'Servidor'
