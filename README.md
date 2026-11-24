# Sistema CRAS

Aplicação Django para gestão de atendimentos do CRAS.

## Executar com Docker

É necessário ter o Docker Desktop com o Compose disponível. Na pasta do projeto, crie o arquivo do banco apenas se ele ainda não existir:

```powershell
if (-not (Test-Path -LiteralPath db.sqlite3)) { New-Item -ItemType File -Path db.sqlite3 }
docker compose run --rm cras python manage.py migrate
docker compose up -d --build
```

A aplicação fica disponível em `http://localhost:8031`. Para usar outro dispositivo na mesma rede, acesse o IP desta máquina na porta `8031` e inclua esse IP em `DJANGO_ALLOWED_HOSTS` no arquivo `compose.yaml`. A rede e o firewall também precisam permitir conexões à porta.

O container usa o arquivo local `db.sqlite3`, que não é incluído no Git nem na imagem. Para criar uma conta administradora em uma instalação nova:

```powershell
docker compose exec cras python manage.py createsuperuser
```

Para parar a aplicação, use `docker compose down`. Para iniciar novamente, use `docker compose up -d`.

## Executar com Python

Use Python 3.12 ou superior e instale `requirements.txt` em um ambiente virtual. Execute `python manage.py migrate` e depois `python manage.py runserver`.

As configurações atuais são voltadas ao desenvolvimento: `DEBUG` está ativo e a chave Django é pública. Antes de uma implantação de produção, configure uma chave privada, desative o modo de depuração e utilize uma configuração de servidor adequada.
