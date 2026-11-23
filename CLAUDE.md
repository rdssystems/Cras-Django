# CLAUDE.md — Gestão CRAS (Django)

## ⚠️ Regras para o agente (leia primeiro)

1. **Leia este arquivo inteiro antes de qualquer mudança.** O Claude Code o carrega no início da sessão; se ele for editado durante a sessão, leia de novo.
2. **Para detalhes**, use o [MAPA_DO_PROJETO.md](MAPA_DO_PROJETO.md): diagrama de modelos, tabela de rotas, histórico de bugs (A1–A7, C1–C2) e achados de risco (B1–B12).
3. **Depois de toda mudança, atualize este arquivo na mesma tarefa.** Vale para mudança de comportamento, modelo, rota, regra de negócio, comando, dependência, convenção ou decisão do usuário.
   - Também atualize o MAPA quando a mudança tocar modelos, rotas, regras ou achados.
   - Registre decisões com data (DD/MM/AAAA) na seção 11.
   - Tire da seção 12 o que for resolvido.
   - **Uma tarefa só termina com a documentação em dia.**
4. Ao terminar, diga ao usuário o que mudou aqui e no MAPA.
5. Fale com o usuário em **português do Brasil**. A interface do sistema também é toda em pt-BR.

---

## 1. O que é

Sistema web interno que **substitui a planilha de controle do CRAS** (Centro de Referência de Assistência Social). Cada aba da planilha virou um app Django.

O núcleo é o fluxo **triagem → fila → atendimento**:

1. A recepção registra quem chegou, com o tipo de fila e a prioridade.
2. A pessoa entra numa de **duas filas**: Atendimento administrativo ou Atendimento psicossocial.
3. Um servidor com o cargo certo clica em **Atender**. O sistema grava o atendimento (`RegistroAtendimento`) e tira a pessoa da fila.

O atendimento é **só presencial**: não existe agendamento online, que foi removido em 23/11/2026.

## 2. Stack e como rodar

| Item | Valor |
|---|---|
| Python / Django | 3.12.3 / 5.2.8 (ambiente global, **sem `requirements.txt`** e sem venv) |
| Outras libs | `openpyxl` 3.1.5 (só para o importador da planilha) |
| Banco | SQLite (`db.sqlite3`, **com dados reais**: ver seção 7) |
| Front | Templates Django + CSS próprio. Sem framework JS. **Apache ECharts 6.1.0** servido localmente, só no Painel |
| Fontes | Google Fonts (Inter, Plus Jakarta Sans, Material Symbols Outlined); dependem de internet |
| Idioma / fuso | `pt-br` / `America/Sao_Paulo`, `USE_TZ=True` |
| Usuário | `AUTH_USER_MODEL = 'usuarios.Usuario'` |

```bash
python manage.py migrate
python manage.py runserver 127.0.0.1:8030   # nesta máquina as portas 80, 3005, 5432-5436, 8000, 8001, 8020, 8080 e 8081 são do Docker
python manage.py test                       # 52 testes
```

`DEBUG = True`, `SECRET_KEY` de desenvolvimento fixa no `settings.py` (pública no GitHub) e sem `STATIC_ROOT`. **Ainda não está pronto para produção** (ver seção 12).

## 3. Estrutura

| App | Modelo | Papel |
|---|---|---|
| `cras` | — | Projeto: `settings.py`, `urls.py`, Painel (`views.inicio`), gráficos (`graficos.py`), template tags (`templatetags/cras_extras.py`), CSS/JS (`static/cras/`) |
| `triagem` | `Atendimento` | Triagem, filas, atender e Controle diário. Comandos `importar_planilha` e `demo_triagens` |
| `atendimentos` | `RegistroAtendimento` | Registro criado automaticamente ao atender; tela só de listagem |
| `certidoes` | `Certidao` | Lista, cria e edita |
| `dsf` | `Dsf` | DSF Concluído: lista e cria (sem edição) |
| `tap` | `TapDiario` | Grade mensal editável |
| `administrativo` | `RegistroAdministrativo` | Histórico 2019–2024 importado da planilha; só leitura, com busca e paginação |
| `usuarios` | `Usuario` | Usuário com `cargo` e gestão de contas em `/usuarios/` |

- **Templates:** ficam em `templates/` (uma pasta por app), mais `base.html`, `inicio.html` e `_campo.html`.
- **Mockup de referência:** `stitch_sistema_de_atendimento_cras/` (`DESIGN.md`, `code.html`, `screen.png`). É só inspiração e os nomes nele são fictícios.

Pontos do modelo de dados:
- Todo FK para `Usuario` usa `SET_NULL`: apagar um servidor não apaga histórico.
- Não existe entidade "Cidadão". Nome e CPF se repetem em cada tabela, sem validação de CPF.

## 4. Regras de negócio

### 4.1 Triagem (`/triagem/registrar/`)
- **Campos:** nome, CPF, **tipo de fila** e **prioridade**.
  - Tipo de fila: *Atendimento administrativo* ou *Atendimento psicossocial*.
  - Prioridade: sem prioridade, 60+, 80+, PcD, Autista, Gestante ou criança de colo, Libras.
- **Status combinado:** o banco guarda um só `status`, no vocabulário da planilha (ex.: `AGUARDANDO ATENDIMENTO PSICOSSOCIAL 60+`). A conversão está em `STATUS_DA_FILA` ([triagem/models.py](triagem/models.py)) e é feita no `save()` do [triagem/forms.py](triagem/forms.py).
- **Resolvido na triagem:** a caixa *Resolvido na própria triagem* grava `ATENDIDO TRIAGEM / ORIENTAÇÃO`, e a pessoa não entra na fila.
- **Status ao todo:** são 17. Destes, **15 são de fila** (`FILAS` / `STATUS_FILA`) e 2 são finais (`ATENDIDO` e `ATENDIDO TRIAGEM / ORIENTAÇÃO`).
  - `REUNIÃO` continua no modelo só para registros antigos e não é oferecido na triagem.
- **Senha:** o `numero` é sequencial por dia, com constraint única (`data`, `numero`). Se houver colisão, o `save()` tenta o próximo número (até 5 vezes).
- **Hora de entrada:** `hora_entrada` usa `default=hora_atual`, e não `auto_now_add`, para o importador gravar a hora da planilha.

### 4.2 Filas e ordem de chamada
- **As duas filas:** `listas_de_chamada(dia)` devolve a fila administrativa e a psicossocial, cada uma com `itens`, `count` e `espera_max`.
- **Ordem de chamada:** **80+** → **demais prioritários** (60+, PcD, Autista, Gestante/colo, Libras) → **geral**. Empate pela senha, ou seja, pela ordem de chegada.
- **Painel (`/`):** mostra as duas filas com os 5 próximos (`ITENS_POR_FILA_NO_PAINEL`).
- **Tela Filas (`/triagem/filas/`):** mostra a lista completa de cada fila, com o botão *Atender*.
- **Atualização:** não há atualização automática; as filas só mudam com F5.

### 4.3 Atender (`/triagem/atender/<pk>/`, POST)
- **Sem atendimento duplo:** `UPDATE ... WHERE status = <status lido>` dentro de `transaction.atomic`. Duplo clique, F5 ou dois servidores ao mesmo tempo não geram atendimento duplicado.
- **Tipo de atendimento:** a lista vem de `RegistroAtendimento.Tipo.choices` e já vem marcada conforme a fila (psicossocial ou administrativo). Um tipo inválido vira ADMINISTRATIVO.
- **Motivos:** múltipla escolha a partir de `RegistroAtendimento.MOTIVOS`.
  - São gravados em `motivo` (texto), separados por `; `, na ordem da lista oficial.
  - `RegistroAtendimento.juntar_motivos()` monta o texto e ignora o que não estiver na lista; a propriedade `.motivos` devolve a lista.

### 4.4 Cargos e permissões
- **Cargos (3):** Assistente Social (`ASSISTENTE_SOCIAL`), Psicólogo(a) (`PSICOLOGO`) e Administrativo (valor gravado `TECNICO_ADMINISTRATIVO`, rótulo "Administrativo").
- **Administrador do sistema:** é o superusuário, que pode não ter cargo.
- **Quem atende o quê:** `pode_atender(usuario, status)`:

| Usuário | Fila psicossocial | Fila administrativa |
|---|---|---|
| Administrador (superusuário) | ✅ | ✅ |
| Psicólogo(a), Assistente Social | ✅ | ✅ |
| Administrativo | ❌ | ✅ |

- **Visualização e outras telas:** todo usuário logado vê as duas filas e acessa todas as outras telas. **Isso ainda não foi decidido pelo usuário** (seção 12).

### 4.5 Contas de usuário (`/usuarios/`)
- **Acesso:** só para superusuário (decorator `somente_administrador`). O menu *Administração → Usuários* só aparece para ele.
- **O que dá para fazer:** criar (a senha é digitada pelo administrador, com os validadores do Django), editar, definir nova senha e desativar/reativar.
- **Sem exclusão:** desativar impede o login e mantém o histórico.
- **Cargo:** obrigatório, exceto para administrador.
- **Administrador do sistema:** a caixa liga `is_superuser` e `is_staff`.
- **Proteção contra se trancar fora:** o administrador não consegue tirar o próprio acesso nem desativar a própria conta.

### 4.6 Outros módulos
- **DSF:** *Benefício solicitado* é uma escolha entre `Dsf.Beneficio`: Cesta Básica, Fralda e Absorvente.
- **Indicador "Atendidos" do Painel:** conta só `ATENDIDO`, sem os resolvidos na triagem. É uma decisão de negócio em aberto (B9 no MAPA).

## 5. Painel e gráficos

- **Arquivos:** os dados são agregados em [cras/graficos.py](cras/graficos.py) e desenhados por [cras/static/cras/js/painel-graficos.js](cras/static/cras/js/painel-graficos.js).
  - O Django entrega tudo via `json_script` e o JS não faz requisições.
- **Seção "Últimos 30 dias"** (sistema novo): atendimentos por dia (colunas empilhadas por desfecho), tipo de atendimento e chegadas por horário.
  - Quem ainda está na fila **hoje** aparece como "Aguardando" (cinza `#7c8ba1`), não como "Sem atendimento".
- **Seção "Histórico administrativo"** (planilha, fev/2019 a set/2024): por mês, motivos, top 10 bairros, faixa etária e quantas vezes cada pessoa foi atendida.
  - Fica **10 min em cache**. A chave usa a contagem e o maior id; por isso, uma edição feita pelo `/admin/` demora até 10 min para aparecer.
- **Regras de cálculo:**
  - Pessoa = CPF (só dígitos, com o zero à esquerda recuperado) ou, sem CPF, o nome sem acento.
  - Meses nas pontas com menos de 10 registros são descartados (datas digitadas erradas).
  - Bairros são agrupados sem acento e com abreviações expandidas.
- **Cores dos gráficos** (validadas para daltonismo): teal `#0d9488`, azul `#3b82f6`, âmbar `#d97706`. Não use o teal da marca (`#0f766e`) em gráficos.
- **Gotcha do ECharts 6:** o `containLabel` mede os rótulos **sem** a fonte global. Ponha `fontFamily` em cada `axisLabel`, `label` e `legend.textStyle`, usando o helper `texto()`, senão o rótulo sai cortado.
- **Tabela:** cada gráfico tem um botão que troca para uma tabela com os mesmos números.

## 6. Front-end: convenções

- **Tema:** tudo em [cras/static/cras/css/tema.css](cras/static/cras/css/tema.css).
  - Os tokens ficam em `:root` (`--primary` `#0f766e`, `--secondary` `#d97706`, `--tertiary` `#3b82f6`…).
  - Títulos em Plus Jakarta Sans e texto em Inter.
  - Não há modo escuro.
- **CSS e JS próprios sempre com `{% static_v 'caminho' %}`** (`cras_extras`), que acrescenta `?v=<mtime>`. Sem isso, o navegador usa o arquivo velho do cache e a página aparece quebrada (aconteceu em 23/11/2026).
- **Campos de formulário:** use `{% include '_campo.html' with campo=form.x %}`, que mostra rótulo, asterisco de obrigatório e erros, e também trata checkbox. Os forms com `novalidate` mostram os erros do Django.
- **Componentes existentes:**
  - estrutura: `card`, `card-pad`, `topo-pagina`, `titulo-secao`, `form-row`;
  - botões: `btn btn-primario` / `btn-secundario` / `btn-verde` / `btn-sm`;
  - etiquetas: `badge-pill badge-{verde,ambar,azul,teal,vermelho,neutro}`;
  - modal: `data-modal-abrir` / `data-modal-fechar`, no `base.html`;
  - cores por fila: `tone-teal` = administrativo e `tone-azul` = psicossocial, via variável `--tone`.
- **Ícones:** Material Symbols, com `<span class="material-symbols-outlined">nome</span>`.
- **Preferência do usuário: interface enxuta.**
  - Nada de caixas "Como funciona", dicas, referências à lei de prioridade ou subtítulos explicativos.
  - Subtítulo só quando mostra um dado (ex.: "5.862 sem motivo informado").
- **Nomes:** os vindos da planilha são em MAIÚSCULAS, e as telas exibem como estão.

## 7. Dados, privacidade e git — CRÍTICO

- **Dados reais de cidadãos:** `db.sqlite3`, `PROJETO BANCO DE DADOS - CRAS.xlsx` e `summary.json` têm **nome, CPF e telefone reais**. Eles **nunca** vão para o git, e o `.gitignore` já os exclui.
- **Repositório:** `origin` = https://github.com/rdssystems/Cras-Django (branch `main`), e é **PÚBLICO**.
  - Antes de qualquer commit, confira `git diff --cached --name-only`.
  - Não coloque dados reais em testes, fixtures, docs ou commits.
- **Git da pasta pessoal:** a pasta do projeto fica dentro de um repositório git acidental na pasta pessoal do usuário.
  - Rode git **sempre de dentro da pasta do projeto**, que tem `.git` próprio.
  - Nunca faça `git add -A` a partir da pasta pessoal.
- **Commit e push só quando o usuário pedir.**
- **Demonstração no banco:** desde 23/11/2026 o banco local tem **dados fictícios de demonstração** (`demo_triagens`).
  - Avise o usuário antes de qualquer uso real, exportação ou relatório.
  - Para limpar: `python manage.py demo_triagens --remover`.
- **Antes de mudar o schema ou rodar comandos que escrevem no banco:** faça uma cópia do `db.sqlite3` fora do projeto.

## 8. Comandos de gestão

| Comando | O que faz |
|---|---|
| `importar_planilha` | Importa a planilha para `RegistroAdministrativo`, `TapDiario`, `RegistroAtendimento` e `Atendimento`. **Já foi rodado.** Recusa rodar de novo sem `--forcar`, porque reimportar **duplica** os dados (só o TAP usa `update_or_create`). |
| `demo_triagens` | Apaga a demonstração anterior e cria cerca de 950 triagens fictícias: 30 dias úteis sem feriados nacionais, mais hoje com cerca de 28 pessoas na fila. Também cria 7 servidores `demo_*` sem senha. A espera de "hoje" é contada a partir da hora em que o comando roda. |
| `demo_triagens --remover` | Apaga só o que está ligado aos usuários `demo_*`, sem tocar em dados reais. |

## 9. Testes

`python manage.py test` → **52 testes, todos passando** (23/11/2026):

| Arquivo | O que cobre |
|---|---|
| [triagem/tests.py](triagem/tests.py) | Filas, ordem de chamada, atender (corrida entre servidores), numeração, importador, triagem com fila + prioridade, motivos múltiplos e demonstração |
| [cras/tests.py](cras/tests.py) | Gráficos do Painel e `static_v` |
| [usuarios/tests.py](usuarios/tests.py) | Contas e cargos |
| [dsf/tests.py](dsf/tests.py) | Benefício do DSF |
| [tap/tests.py](tap/tests.py) | TAP |

Certidões, administrativo e a lista de atendimentos ainda não têm testes. Toda mudança de regra deve vir com teste.

## 10. Ambiente (Windows) — gotchas

- **Shells:** há PowerShell e Git Bash. No Git Bash, argumentos que começam com `/` viram caminhos do Windows (`/triagem/` → `C:/Program Files/Git/triagem/`). Passe URLs sem a barra inicial ou use `MSYS_NO_PATHCONV=1`.
- **Rodar código Django avulso:** pipe para `manage.py shell` quebra com BOM. Use:
  `python -c "import django,os,sys; sys.path.insert(0,'.'); os.environ['DJANGO_SETTINGS_MODULE']='cras.settings'; django.setup(); ..."`
- **Arquivos com aspas e acentos:** heredoc no Bash já falhou com esse conteúdo. Prefira a ferramenta de escrita de arquivos.
- **Migrações:** são aplicadas na hora com `migrate`. Mudança no `settings.py` exige reiniciar o `runserver`.
- **Screenshots para conferir telas:**
  - Use `playwright-core` (npm, numa pasta temporária fora do projeto) com `channel: 'msedge'`; o Python daqui não tem playwright.
  - Para logar, crie uma sessão por `SessionStore` / `force_login` e **apague a sessão depois**.
  - Num formulário, clique em `main form button[type=submit]`: o primeiro submit da página é o "Sair" da barra superior.

## 11. Decisões do usuário (registro)

| Data | Decisão |
|---|---|
| 17/11/2026 | Tela Filas em linhas, duas listas; ordem 80+ → demais prioritários → geral, empate pela senha. Libras como prioritário foi suposição do agente; confirmar se o usuário questionar. |
| 17/11/2026 | Interface enxuta, sem textos explicativos (seção 6). |
| 23/11/2026 | Gráficos com Apache ECharts no Painel, servido localmente. |
| 23/11/2026 | Atendimento só presencial: status `AGENDAMENTO ONLINE` removido (migração `triagem/0004`). |
| 23/11/2026 | Cargos: só Assistente Social, Psicólogo(a) e Administrativo; Coordenador(a) removido. Contas criadas no front pelo administrador. |
| 23/11/2026 | Triagem com tipo de fila + prioridade; Painel com duas filas; motivos de múltipla escolha; benefício do DSF como lista de seleção. |
| 23/11/2026 | A caixa "Resolvido na própria triagem" e a saída de `REUNIÃO` da triagem foram escolhas do agente para não perder funções; confirmar se o usuário questionar. |
| 23/11/2026 | Código publicado no GitHub (repositório público), sem os dados reais. |

## 12. Pendências (próximos passos)

1. **Permissões por cargo:** aguarda a resposta do usuário. Hoje, a sugestão do agente é:
   - Psicólogo(a) e Assistente Social continuam atendendo a fila administrativa.
   - O Administrativo continua vendo os nomes da fila psicossocial.
   - "Atendimento psicossocial" só pode ser registrado por Psicólogo(a) ou Assistente Social.
   - Falta definir quem acessa Certidões, DSF, TAP e Histórico (que tem CPF).
2. **Paginação em `/atendimentos/`** (B6): com 675 registros a página tem 61 mil px e leva 1,6 s.
3. **Controle diário com dia cheio** (B12): a tabela estoura o card e o CPF e os nomes quebram em várias linhas.
4. **Produção** (B2): `SECRET_KEY` e `DEBUG` por variável de ambiente (a chave atual está pública), `requirements.txt`, `STATIC_ROOT` e `ALLOWED_HOSTS`.
5. **Registro inválido C1:** um `RegistroAtendimento` de importação com nome vazio. Decidir se apaga.
6. **Indicador "Atendidos"** (B9): decidir se conta os resolvidos na triagem.
7. **Atualização automática das filas** (B7), por exemplo recarregar a cada 30 s.

## 13. Checklist ao terminar uma tarefa

- [ ] `python manage.py test` passando, com testes novos para a regra nova.
- [ ] `python manage.py makemigrations --check` sem pendências, e `migrate` aplicado.
- [ ] Telas conferidas (screenshot) quando houver mudança visual.
- [ ] **Este CLAUDE.md atualizado** (regras, decisões, pendências, contagem de testes) e o MAPA, se for o caso.
- [ ] Nada de dado real ou segredo novo no que vai para o git.
