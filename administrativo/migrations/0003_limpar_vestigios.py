from django.db import migrations


def apagar_tipo_de_conteudo(apps, schema_editor):
    """Leva junto as permissões e o log do /admin/, que guarda o nome de cada registro editado."""
    apps.get_model('contenttypes', 'ContentType').objects.filter(app_label='administrativo').delete()


def compactar_banco(apps, schema_editor):
    """No SQLite, apagar a tabela não apaga os dados do arquivo: eles ficam em páginas livres e no WAL."""
    if schema_editor.connection.vendor != 'sqlite':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('VACUUM')
        cursor.execute('PRAGMA wal_checkpoint(TRUNCATE)')


class Migration(migrations.Migration):
    atomic = False  # o VACUUM não roda dentro de transação

    dependencies = [
        ('administrativo', '0002_remover_historico'),
        ('admin', '0003_logentry_add_action_flag_choices'),
        ('auth', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(apagar_tipo_de_conteudo, migrations.RunPython.noop, atomic=True),
        migrations.RunPython(compactar_banco, migrations.RunPython.noop, atomic=False),
    ]
