from django.db import migrations


class Migration(migrations.Migration):
    """Apaga o histórico administrativo: ele veio da planilha e não deveria estar no sistema."""

    dependencies = [('administrativo', '0001_initial')]

    operations = [migrations.DeleteModel(name='RegistroAdministrativo')]
