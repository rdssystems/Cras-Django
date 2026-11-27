from django.apps import AppConfig


class AdministrativoConfig(AppConfig):
    """App desativado: o histórico administrativo foi removido em 27/11/2026.

    Só as migrações ficam, para apagar a tabela e os dados de qualquer banco que rode o `migrate`.
    Não recriar o modelo nem voltar a importar essa aba da planilha.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'administrativo'
