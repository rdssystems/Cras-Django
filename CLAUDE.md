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

Sistema web interno que **substitui a planilha de controle do CRAS** (Centro de Referência de Assistência Social). Cada aba da planilha virou um app Django, exceto o histórico administrativo antigo, **removido em 27/11/2026** (seção 7).

O núcleo é o fluxo **triagem → fila → atendimento**:

1. A recepção registra quem chegou, com o tipo de fila e a prioridade.
2. A pessoa entra numa de **duas filas**: Atendimento administrativo ou Atendimento psicossocial.
3. Um servidor com o cargo certo clica em **Atender**. O sistema grava o atendimento (`RegistroAtendimento`) e tira a pessoa da fila.

O atendimento é **só presencial**: não existe agendamento online, que foi removido em 23/11/2026.

## 2. Stack e como rodar

| Item | Valor |
|---|---|
| Python / Django | 3.12 / **6.1.2**, versões fixadas em `requirements.txt` (com `openpyxl`, `gunicorn` e `whitenoise`) |
| Ambiente local | `.venv` na pasta do projeto (ignorado pelo git). O Python global da máquina tem Django 5.2 e **não** tem whitenoise: não rode o projeto por ele |
| Banco | SQLite em modo WAL (`db.sqlite3` local, **com dados reais**: ver seção 7). Em produção, o caminho vem de `DJANGO_DB_PATH` |
| Front | Templates Django + CSS próprio (`tema.css`), Bootstrap 5.3 e Bootstrap Icons via CDN. **Apache ECharts 6.1.0** servido localmente, só no Painel |
| Fontes | Google Fonts: Lexend (texto), Kalam (fita da marca), Material Symbols Outlined. Dependem de internet |
| Idioma / fuso | `pt-br` / `America/Sao_Paulo`, `USE_TZ=True` |
| Usuário | `AUTH_USER_MODEL = 'usuarios.Usuario'` |

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # uma vez
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py runserver 127.0.0.1:8030   # nesta máquina 80, 3005, 5432-5436, 8000, 8001, 8020, 8080 e 8081 são do Docker
.venv/Scripts/python manage.py test
```

Outras formas de rodar:
- **Docker de desenvolvimento:** `compose.yaml`, com `runserver` na porta 8031 e o `db.sqlite3` local montado. É o caminho do README e do Isaque.
- **Produção:** `compose.prod.yaml`, com gunicorn, configurado por `.env`. Ver a seção 7.1.

**Configuração por ambiente** (`cras/settings.py`):
- Sem variáveis, vale o modo de desenvolvimento: `DEBUG` ligado e chave pública `django-insecure-…`.
- Com `DJANGO_DEBUG=False`, a `DJANGO_SECRET_KEY` é **obrigatória** (sem ela o sistema não sobe), os cookies ficam `Secure` e os estáticos são servidos pelo whitenoise.
- Outras variáveis: `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` (com a porta) e `DJANGO_DB_PATH`. O modelo está em `.env.example`.

## 3. Estrutura

| App | Modelo | Papel |
|---|---|---|
| `cras` | — | Projeto: `settings.py`, `urls.py`, Painel (`views.inicio`), gráficos (`graficos.py`), template tags (`templatetags/cras_extras.py`), CSS/JS (`static/cras/`) |
| `triagem` | `Atendimento` | Triagem, filas, atender e Controle diário. Comandos `importar_planilha` e `demo_triagens` |
| `atendimentos` | `RegistroAtendimento` | Registro criado automaticamente ao atender; tela só de listagem |
| `certidoes` | `Certidao` | Solicitação de 2ª via (ficha do cartório) e acompanhamento até a entrega: lista, cria e edita. Ver 4.6 |
| `dsf` | `Dsf`, `MembroFamiliar` | Menu "DSF": ficha do Diagnóstico Sócio Familiar (cria e edita). Ver 4.6 |
| `dmae` | `IsencaoDmae`, `MembroDmae`, `EvolucaoDmae` | Menu "Isenção DMAE": Requerimento DMAE (lista, cria e edita). Ver 4.6 |
| `propao` | `RequerimentoProPao`, `PessoaProPao`, `ProcedimentoProPao` | Menu "PRÓ-PÃO": Requerimento do PRÓ-PÃO (lista, cria e edita). Ver 4.6 |
| `tap` | `TapDiario` | Grade mensal editável |
| `administrativo` | — | **Desativado em 27/11/2026.** Só as migrações, que apagam o antigo histórico de qualquer banco. Não recriar |
| `usuarios` | `Usuario` | Usuário com `cargo` e gestão de contas em `/usuarios/` |

- **Templates:** ficam em `templates/` (uma pasta por app), mais `base.html`, `inicio.html` e `_campo.html`.
- **Mockup de referência:** `stitch_sistema_de_atendimento_cras/` (`DESIGN.md`, `code.html`, `screen.png`). É só inspiração e os nomes nele são fictícios.

Pontos do modelo de dados:
- Todo FK para `Usuario` usa `SET_NULL`: apagar um servidor não apaga histórico.
- Não existe entidade "Cidadão". Nome e CPF se repetem em cada tabela. O CPF só é validado na triagem, no DSF, em Certidões, na Isenção DMAE e no PRÓ-PÃO, com a mesma função (`cras/validadores.py`).
- Peças comuns às fichas ficam no projeto: `cras/campos.py` (campos de modelo), `cras/escolhas.py` (Sim/Não, estado civil, tipo de solicitação, resultado do deferimento), `cras/formularios.py` (datas, `ReaisField`, CPF, linhas das tabelas), `cras/validadores.py` (CPF e CEP) e `cras/fichas.py` (fluxo de salvar a ficha e totais da lista).

## 4. Regras de negócio

### 4.1 Triagem (`/triagem/registrar/`)
- **Campos:** nome, CPF, **tipo de fila** e **prioridade**.
  - Tipo de fila: *Atendimento administrativo* ou *Atendimento psicossocial*.
  - Prioridade: sem prioridade, 60+, 80+, PcD, Autista, Gestante ou criança de colo, Libras.
- **Status combinado:** o banco guarda um só `status`, no vocabulário da planilha (ex.: `AGUARDANDO ATENDIMENTO PSICOSSOCIAL 60+`). A conversão está em `STATUS_DA_FILA` ([triagem/models.py](triagem/models.py)) e é feita no `save()` do [triagem/forms.py](triagem/forms.py).
- **Resolvido na triagem:** a caixa *Orientações Realizadas na triagem* grava `ATENDIDO TRIAGEM / ORIENTAÇÃO`, e a pessoa não entra na fila.
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

- **Visualização e outras telas:** todo usuário logado vê as duas filas e acessa as outras telas, com uma exceção: a ficha do DSF (só Assistente Social, Psicólogo(a) e administrador, seção 4.6). **O restante ainda não foi decidido pelo usuário** (seção 12).

### 4.5 Contas de usuário (`/usuarios/`)
- **Acesso:** só para superusuário (decorator `somente_administrador`). O menu *Administração → Usuários* só aparece para ele.
- **O que dá para fazer:** criar (a senha é digitada pelo administrador, com os validadores do Django), editar, definir nova senha e desativar/reativar.
- **Sem exclusão:** desativar impede o login e mantém o histórico.
- **Cargo:** obrigatório, exceto para administrador.
- **Administrador do sistema:** a caixa liga `is_superuser` e `is_staff`.
- **Proteção contra se trancar fora:** o administrador não consegue tirar o próprio acesso nem desativar a própria conta.

### 4.6 Outros módulos
- **Quatro formulários (26/11/2026):** o menu *Gestão* tem uma opção para cada página: **DSF** (`/dsf/`), **Certidões** (`/certidoes/`), **Isenção DMAE** (`/isencao-dmae/`) e **PRÓ-PÃO** (`/pro-pao/`). Não há abas dentro das páginas (foram criadas e retiradas no mesmo dia, a pedido).
  - Cada página vai ter o próprio botão (*Novo DSF*, *Nova Certidão*…), o próprio formulário e a própria lista, e os registros precisarão ser **deferidos depois**. O usuário enviou um documento Word por página: **não inventar campos que não estejam neles**.
  - Hoje: **as quatro páginas têm a ficha nova** (abaixo). Faltam o deferimento e os PDFs.
- **Ficha do DSF (26/11/2026)**, cópia do documento Word "Diagnóstico Sócio Familiar – DSF" do CRAS Morumbi:
  - *Novo DSF* (`/dsf/novo/`) e *Editar* (`/dsf/<pk>/editar/`), em `templates/dsf/form.html`, na ordem do papel: 1. Solicitação; I. Identificação; II. Composição familiar (4 linhas, com adicionar e remover); III. Condição socioeconômica; 2. Abordagem domiciliar: IV. Habitabilidade, VI. Saúde (o documento não tem a seção V), VII. Benefícios sociais e as duas abordagens (data e técnico).
  - Obrigatórios: **data, benefício e nome**. O resto é preenchido aos poucos, porque a visita domiciliar vem depois da solicitação.
  - **Quem faz a ficha:** só **Assistente Social** e **Psicólogo(a)**, além do administrador do sistema (`pode_preencher_dsf` em `dsf/models.py`). O Administrativo vê a lista, mas não tem *Novo DSF* nem *Editar*, e as rotas o recusam.
  - A ficha nasce **PENDENTE** (`resultado` vazio). Só um DSF pendente pode ser editado (`Dsf.pendente`).
  - **VIII. Parecer não está na ficha**: Deferida/Indeferida, texto do parecer, técnico, CRESS/MG e data serão a etapa de deferimento (a fazer). Depois dela vem o **PDF** no layout do documento (a fazer).
  - `tecnico_responsavel` é quem criou a ficha; editar não troca.
  - Valores em reais aceitam `1.412,50`, `1412,5` ou `R$ 600` (`ReaisField`). Renda familiar e per capita são digitadas, sem cálculo automático.
  - Registros da planilha têm `ficha_preenchida=False`: não contam como pendentes e não abrem a ficha.
- **DSF:** *Benefício solicitado* é uma escolha entre `Dsf.Beneficio`: Cesta Básica, Fralda e Absorvente.
  - O técnico é a conta de quem cadastrou (`tecnico_responsavel`) ou o nome vindo da planilha (`tecnico_legado`). As telas usam `tecnico_nome`.
- **Ficha de Certidões (26/11/2026)**, cópia do documento Word "Solicitação de Registro Civil":
  - *Nova certidão*: 2ª via de **Nascimento, Casamento, Óbito** e **Com averbação** (pelo menos uma marcada), data e cidade do cartório (já vem `UBERLÂNDIA - MG`); registrado(a): nome (`de_quem`), filiação, nascimento, CPF, telefone, endereço, bairro, CadÚnico e NIS; responsável que assina (`quem_solicitou`) e parentesco.
  - Obrigatórios: tipo, data, nome e nome do responsável.
  - **Acompanhamento** (recebimento, contato, entrega, observações) aparece só no *Editar*.
  - Qualquer usuário logado cria e edita (o usuário não definiu cargo para certidões).
  - Registros da planilha (`ficha_preenchida=False`) podem ter o acompanhamento editado sem marcar o tipo.
  - Falta: deferimento e PDF. O texto legal, o cabeçalho e as assinaturas são fixos e entram só no PDF. No documento original há "CADSTRADO" e um número de 11 dígitos solto no meio da declaração: **não copiar esses erros para o PDF** (o número não é registrado em lugar nenhum do projeto).
- **Certidões:** o servidor é a conta (`servidor`) ou o nome vindo da planilha (`servidor_legado`). As telas usam `servidor_nome`. Há também um campo livre de `observacoes`.
- **Ficha da Isenção DMAE (26/11/2026)**, cópia do documento Word "Requerimento DMAE" (Leis 309 e 315 de 2003):
  - *Novo Requerimento DMAE* (`/isencao-dmae/novo/`) e *Editar* (`/isencao-dmae/<pk>/editar/`): solicitação (**1ª vez** ou **Renovação**), data e código do imóvel; I. Identificação; II. Composição familiar (2 linhas, com adicionar e remover) e renda familiar digitada; III. Situação habitacional, separada em **tipo** (casa, barraco, apartamento) e **situação** (própria, alugada, financiada, cedido, invasão), e "possui mais de um imóvel?"; IV. Consumo de água de 3 meses (`MM/AAAA` e m³); V. Evolução (data e procedimento, quantas linhas quiser); VI. Parecer social.
  - Obrigatórios: tipo de solicitação, data e nome. Na evolução, uma linha começada exige data e procedimento.
  - O **consumo médio é calculado** (`IsencaoDmae.consumo_medio`): média dos meses preenchidos, com 1 casa decimal. Não é gravado.
  - Nasce **PENDENTE** (`resultado` vazio) e só pode ser editado enquanto pendente. `servidor` é quem criou.
  - Qualquer usuário logado cria e edita, inclusive o parecer social (o usuário não definiu cargo).
  - Falta: deferimento e PDF (cabeçalho, leis e assinaturas entram só no PDF). Ao fazer o deferimento, decidir se a evolução continua aberta depois dele.
- **Ficha do PRÓ-PÃO (26/11/2026)**, cópia do documento Word "Requerimento do PRÓ-PÃO":
  - *Novo Requerimento PRÓ-PÃO* (`/pro-pao/novo/`) e *Editar* (`/pro-pao/<pk>/editar/`): tipo (**1ª vez** ou **Renovação**) e data; I. Identificação (com data de nascimento, número, complemento, CEP, documento de identidade e SSP/UF); II. Composição familiar (4 linhas na tela, o papel tem 8); III. Renda familiar; IV. Situação habitacional (própria, cedida, alugada, financiada ou ocupação, com valor e detalhe da ocupação); V. Análise do sistema (2º imóvel, em nome de titular e/ou cônjuge, endereço, sistema e data); Procedimentos (data e texto, quantas linhas quiser).
  - Obrigatórios: tipo, data e nome. **Titular/Cônjuge** só podem ser marcados com "Possui 2º imóvel". O CEP é gravado como `00000-000`.
  - Nasce **PENDENTE** e só pode ser editado enquanto pendente. `servidor` é quem criou. Qualquer usuário logado preenche tudo, inclusive a seção V.
  - Falta: deferimento e PDF (cabeçalho, declaração de veracidade e assinaturas entram só no PDF).
- **Indicador "Atendidos" do Painel:** conta só `ATENDIDO`, sem os resolvidos na triagem. É uma decisão de negócio em aberto (B9 no MAPA).

## 5. Painel e gráficos

- **Arquivos:** os dados são agregados em [cras/graficos.py](cras/graficos.py) e desenhados por [cras/static/cras/js/painel-graficos.js](cras/static/cras/js/painel-graficos.js).
  - O Django entrega tudo via `json_script` e o JS não faz requisições.
- **Seção "Últimos 30 dias"** (sistema novo): atendimentos por dia (colunas empilhadas por desfecho), tipo de atendimento e chegadas por horário.
  - Quem ainda está na fila **hoje** aparece como "Aguardando" (cinza `#7c8ba1`), não como "Sem atendimento".
- É a única seção. A *Histórico administrativo* (5 gráficos da planilha) foi removida em 27/11/2026.
- **Cores dos gráficos** (validadas para daltonismo): teal `#0d9488`, azul `#3b82f6`, âmbar `#d97706`. Não use o teal da marca (`#0f766e`) em gráficos.
- **Gotcha do ECharts 6:** o `containLabel` mede os rótulos **sem** a fonte global. Ponha `fontFamily` em cada `axisLabel`, `label` e `legend.textStyle`, usando o helper `texto()`, senão o rótulo sai cortado.
- **Tabela:** cada gráfico tem um botão que troca para uma tabela com os mesmos números.

## 6. Front-end: convenções

- **Padrão visual da Secretaria** (desde 24/11/2026): siga o [front-rules.md](front-rules.md), que é o manual comum aos sistemas (referência: Naicas).
- **Tema:** tudo em [cras/static/cras/css/tema.css](cras/static/cras/css/tema.css).
  - Um segundo bloco `:root` aplica a paleta da Secretaria sobre os tokens antigos: `--cor-primaria` anil `#2b3a8c`, `--cor-critica` urucum `#c8471f`, `--cor-atencao` ipê `#f2b705`, `--cor-sucesso` folha `#2e7a4c` e `--cor-fundo` `#f3f4f8`.
  - Fonte Lexend; a marca é a "fita" `marca-fita` (Kalam). A navegação fica numa barra superior, com o menu "Gestão" recolhível.
  - Não há modo escuro.
- **CSS e JS próprios sempre com `{% static_v 'caminho' %}`** (`cras_extras`), que acrescenta `?v=<mtime>`. Sem isso, o navegador usa o arquivo velho do cache e a página aparece quebrada (aconteceu em 23/11/2026).
- **Campos de formulário:** use `{% include '_campo.html' with campo=form.x %}`, que mostra rótulo, asterisco de obrigatório e erros, e também trata checkbox. Os forms com `novalidate` mostram os erros do Django.
- **Escolha única em botões:** `{% include '_opcoes.html' with campo=form.x %}` (radio). Fichas longas usam a classe `ficha`.
- **Linhas que entram e saem** (composição familiar, evolução): `{% include '_tabela_linhas.html' with formset=... botao='...' icone='...' %}` com o script `cras/js/ficha.js`, que também limpa o campo de CPF. O formset precisa de `can_delete=True` e prefixo próprio.
- **Ficha nova com tabelas:** a view usa `tela_de_ficha()` e `contar_situacoes()` (`cras/fichas.py`); as linhas usam `LinhaForm` ou `LinhaDePessoaForm` e `formset_de_linhas()`. Não copie esse fluxo para dentro do app.
- **Lista com deferimento:** `_cartoes_de_situacao.html` (pendentes, deferidos, indeferidos) e `_situacao.html` (etiqueta; o objeto precisa de `resultado` e `pendente`).
- **Datas:** sempre com `campo_de_data()` de `cras/formularios.py`; sem o formato ISO, o `<input type="date">` abre vazio na edição.
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
- **Commit e push: liberados** (autorização permanente do usuário, 26/11/2026).
  - Commite e envie ao terminar cada mudança testada, e depois atualize a VPS quando a mudança for para produção.
  - A permissão fica em `.claude/settings.local.json` (local, fora do git).
  - Continue conferindo o que entra no commit: nada de dados reais, `.env` ou o `klisman-note` local do `settings.py`.
- **Demonstração no banco:** desde 23/11/2026 o banco local tem **dados fictícios de demonstração** (`demo_triagens`).
  - Avise o usuário antes de qualquer uso real, exportação ou relatório.
  - Para limpar: `python manage.py demo_triagens --remover`.
- **Antes de mudar o schema ou rodar comandos que escrevem no banco:** faça uma cópia do `db.sqlite3` fora do projeto.
- **O banco da VPS é outro**, separado do local. Ele começou vazio em 26/11/2026 e, no mesmo dia, recebeu a planilha atual do CRAS Morumbi (`BANCO DE DADOS MORUMBI.xlsx`, a pedido do usuário). Nunca copie o banco local (com dados antigos e com a demonstração) para a VPS sem o usuário pedir.
- **Histórico administrativo removido (27/11/2026):** os registros da aba `1S2024 ATENDIMENTO ADMINISTRATI` não deveriam estar no sistema. Página, menu, gráficos, modelo e dados foram apagados.
  - Não voltar a importar essa aba. Uma cópia antiga do banco só pode ser restaurada rodando o `migrate` em seguida, que apaga o histórico de novo.
- **Planilhas:** toda planilha `.xlsx` na pasta tem dados reais e fica fora do git. Depois de importada na VPS, o arquivo é apagado de lá.

### 7.1 Produção (VPS, desde 26/11/2026)

- **Endereço público:** https://servidor-test.taile3dafe.ts.net:10000, pelo **Tailscale Funnel** (público na internet).
  - No mesmo host, a 443 é o Naicas e a 8443 é o Jellyfin. A 10000 era a última porta de Funnel livre.
- **Servidor:** `servidor-test` (ZimaOS), alcançado pelo IP do Tailscale. O usuário e a senha do SSH ficam com o usuário e não são registrados em lugar nenhum.
  - Docker exige `sudo` (com senha).
  - O OpenSSH 10 de lá bloqueia por alguns segundos quem errou o login (PerSourcePenalties). Espere e tente de novo; não fique testando usuários.
- **Pasta:** `/DATA/AppData/Cras-django`, um `git clone` do GitHub, como o Naicas.
  - `.env` com `chmod 600`, chave própria gerada no servidor.
  - O banco fica em `dados/db.sqlite3`, uma pasta montada inteira por causa dos arquivos do WAL.
- **Container:** `cras-app` (`compose.prod.yaml`), escutando só em `127.0.0.1:8031`.
  - Ao subir, roda `migrate`, `collectstatic` e gunicorn com 3 workers.
- **Funnel:** `docker exec tailscale tailscale funnel --bg --https=10000 http://127.0.0.1:8031`.
  - O Tailscale roda no container `tailscale`, com rede do host.
  - Para ver a configuração: `docker exec tailscale tailscale funnel status`.
- **Atualizar:** `cd /DATA/AppData/Cras-django && git pull && sudo docker compose -f compose.prod.yaml up -d --build`.
- **Versão no ar (27/11/2026):** commit `68f52fc`, com os motivos novos e os quatro formulários (migrações `atendimentos/0005`, `certidoes/0004`, `dsf/0005`, `dmae/0001` e `propao/0001`). Cópias manuais do banco ficam em `dados/` (`backup-antes-*.sqlite3`).
- **Logs:** `sudo docker logs -f cras-app`.
- **Verificar de fora sem SSH:** `nslookup servidor-test.taile3dafe.ts.net 1.1.1.1` e `curl --resolve servidor-test.taile3dafe.ts.net:10000:<IP público do relay> https://servidor-test.taile3dafe.ts.net:10000/login/`.

## 8. Comandos de gestão

| Comando | O que faz |
|---|---|
| `importar_planilha --arquivo <xlsx>` | Importa a planilha do CRAS: controle diário (`Atendimento`), Registro de Atendimentos, TAP 2026, **Certidões** e **DSF**. A aba do histórico administrativo é ignorada. Detalhes abaixo. |
| `demo_triagens` | Apaga a demonstração anterior e cria cerca de 950 triagens fictícias: 30 dias úteis sem feriados nacionais, mais hoje com cerca de 28 pessoas na fila. Também cria 7 servidores `demo_*` sem senha. A espera de "hoje" é contada a partir da hora em que o comando roda. |
| `demo_triagens --remover` | Apaga só o que está ligado aos usuários `demo_*`, sem tocar em dados reais. |

**Como o `importar_planilha` funciona:**
- **Tudo ou nada:** roda numa transação única. Se algo falhar, o banco fica como estava.
- **Trava:** recusa rodar se o banco já tiver qualquer triagem, atendimento, certidão ou DSF, porque a importação pode **duplicar** os dados (o TAP usa `update_or_create` e não entra na conferência). Para forçar, use `--forcar`.
- **Já rodado:** no banco local, com a planilha antiga; na VPS, em 26/11/2026, com `BANCO DE DADOS MORUMBI.xlsx`.
- **Motivos:** as 4 colunas de motivo viram a lista separada por `; `, como na múltipla escolha. Os textos ficam como estão na planilha, sem trocar pela lista oficial.
- **Certidões:**
  - quando a coluna de data traz texto (ex.: "entregue para a mãe em 20/02/2026"), o importador usa a primeira data do texto e guarda o texto inteiro em `observacoes`;
  - datas digitadas na coluna de nome viram texto `dd/mm/aaaa`;
  - o nome do servidor vai para `servidor_legado`;
  - linhas sem data de solicitação são ignoradas.
- **DSF:**
  - "CESTA BÁSICA - DSF" vira `CESTA BÁSICA`;
  - o nome do técnico vai para `tecnico_legado`;
  - sem resultado na planilha, fica `''` e a lista mostra "—", sem inventar "deferido".

## 9. Testes

`.venv/Scripts/python manage.py test` → **100 testes, 99 passando** (27/11/2026).

A falha é `test_sao_duas_filas_administrativa_e_psicossocial`: o commit `c1c2cae` (24/11) tirou do Painel os cards das duas filas, e o teste ainda os procura. Falta o usuário decidir entre ajustar o teste e devolver as filas ao Painel (seção 12).

| Arquivo | O que cobre |
|---|---|
| [triagem/tests.py](triagem/tests.py) | Filas, ordem de chamada, atender (corrida entre servidores), numeração, importador, triagem com fila + prioridade, motivos múltiplos e demonstração |
| [cras/tests.py](cras/tests.py) | Gráficos do Painel e `static_v` |
| [usuarios/tests.py](usuarios/tests.py) | Contas e cargos |
| [dsf/tests.py](dsf/tests.py) | Ficha do DSF (criar, editar, pendente, valores, composição familiar, permissão) e menu Gestão |
| [certidoes/tests.py](certidoes/tests.py) | Ficha da certidão, edição e datas na tela |
| [dmae/tests.py](dmae/tests.py) | Requerimento DMAE: criar, editar, consumo médio, mês/ano, evolução e deferido sem edição |
| [propao/tests.py](propao/tests.py) | Requerimento do PRÓ-PÃO: criar, editar, CEP, 2º imóvel, procedimentos e deferido sem edição |
| [tap/tests.py](tap/tests.py) | TAP |

A lista de atendimentos ainda não tem testes. Toda mudança de regra deve vir com teste.

## 10. Ambiente (Windows) — gotchas

- **Shells:** há PowerShell e Git Bash. No Git Bash, argumentos que começam com `/` viram caminhos do Windows (`/triagem/` → `C:/Program Files/Git/triagem/`). Passe URLs sem a barra inicial ou use `MSYS_NO_PATHCONV=1`.
- **Rodar código Django avulso:** pipe para `manage.py shell` quebra com BOM. Use:
  `python -c "import django,os,sys; sys.path.insert(0,'.'); os.environ['DJANGO_SETTINGS_MODULE']='cras.settings'; django.setup(); ..."`
- **Arquivos com aspas e acentos:** heredoc no Bash já falhou com esse conteúdo. Prefira a ferramenta de escrita de arquivos.
- **Migrações:** são aplicadas na hora com `migrate`. Mudança no `settings.py` exige reiniciar o `runserver`.
- **Python:** use sempre o do `.venv` (`.venv/Scripts/python`). O global não tem as dependências do `requirements.txt`.
- **Servidor esquecido rodando:** um `runserver` de uma sessão anterior pode continuar ocupando a 8030, e o recarregador troca o PID do processo filho a cada mudança de arquivo. Para encontrá-lo: `Get-NetTCPConnection -LocalPort 8030 -State Listen` e, depois, o `ParentProcessId` do processo.
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
| 24/11/2026 | Commits do Isaque Miranda, colaborador:<br>• identidade visual da Secretaria (`front-rules.md`);<br>• Docker de desenvolvimento e `requirements.txt` com Django 6.1.2;<br>• validação do CPF na triagem (11 números e dígitos verificadores);<br>• Controle diário fora do menu principal, como aba do Painel;<br>• Painel sem os cards das filas. |
| 26/11/2026 | Deploy na VPS com **banco vazio** e acesso **público pelo Funnel (porta 10000)**; ajustes de produção commitados no GitHub (seção 7.1). |
| 26/11/2026 | O banco local é antigo. A planilha atual do CRAS Morumbi foi importada direto na VPS, com o importador ampliado para Certidões e DSF. Multiunidade (ex.: "CRAS Morumbi") ficou para depois. |
| 26/11/2026 | Commit e push liberados de forma permanente: o agente commita, envia e atualiza a VPS sem pedir. |
| 26/11/2026 | Novos motivos no *Atender* e "Cesta básica" renomeada para "Solicitação de cesta básica". **Só no localhost** até o usuário mandar subir (pendência 2.1). |
| 26/11/2026 | Na triagem, a caixa passa a se chamar "Orientações Realizadas na triagem (não entra na fila)". No menu, "DSF Concluído" vira "DSF", sem o botão *Novo DSF*, com 4 abas (DSF, Certidões, Isenção DMAE e PRÓ-PÃO), cada uma com formulário próprio a enviar (seção 4.6). Por enquanto só no localhost (pendência 2.1). |
| 26/11/2026 | Ficha completa do DSF a partir do documento Word do CRAS, com lista e situação Pendente. Deferimento e PDF ficam para depois. A divisão (parecer fora da ficha, obrigatórios, quem pode editar) foi escolha do agente; confirmar se o usuário questionar. Só no localhost. |
| 26/11/2026 | A ficha do DSF é feita por Assistente Social ou Psicólogo(a). O acesso do administrador do sistema foi mantido pelo agente, como no *Atender*. Logos ficam para mais adiante. |
| 26/11/2026 | Abas dentro do DSF retiradas: DSF, Certidões, Isenção DMAE e PRÓ-PÃO viram opções do menu *Gestão*. |
| 26/11/2026 | Ficha nova de Certidões a partir do documento Word. Escolhas do agente: tipos como caixas de marcar, acompanhamento só na edição, sem restrição de cargo. Só no localhost. |
| 26/11/2026 | Ficha da Isenção DMAE a partir do documento Word, com a Evolução em linhas adicionáveis (sugestão do usuário). Escolhas do agente: app próprio `dmae`, situação habitacional em dois grupos, consumo médio calculado, parecer social dentro da ficha, sem restrição de cargo. Só no localhost. |
| 26/11/2026 | Ficha do PRÓ-PÃO a partir do documento Word, último dos quatro formulários. Escolhas do agente: app próprio `propao`, 4 linhas iniciais na composição familiar, tabela final chamada "Procedimentos", seção V sempre visível e sem restrição de cargo. Só no localhost. |
| 27/11/2026 | O usuário autorizou subir só a correção das datas de certidão (commit `9e96669`); VPS atualizada no mesmo dia. Conferidas as 490 certidões contra a planilha: nenhuma data perdida. O restante continua apenas no localhost. |
| 27/11/2026 | O usuário mandou publicar o que estava só no localhost: motivos novos, rótulo da triagem, menu *Gestão* e os quatro formulários. Os "só no localhost" acima são anteriores a esta publicação. |
| 27/11/2026 | **Histórico administrativo removido** do sistema, do localhost e da produção, com os gráficos do Painel que o usavam: os dados vieram da planilha no início do desenvolvimento e não deveriam ter subido. Escolhas do agente: apagar também o modelo e a importação, compactar o banco e tirar o histórico das cópias de segurança. |

## 12. Pendências (próximos passos)

1. **Permissões por cargo:** aguarda a resposta do usuário. Hoje, a sugestão do agente é:
   - Psicólogo(a) e Assistente Social continuam atendendo a fila administrativa.
   - O Administrativo continua vendo os nomes da fila psicossocial.
   - "Atendimento psicossocial" só pode ser registrado por Psicólogo(a) ou Assistente Social.
   - Já definido: a ficha do DSF é de Assistente Social e Psicólogo(a). Falta definir quem acessa Certidões, TAP, a lista do DSF e as próximas abas.
2. **Teste das filas no Painel:** ajustar o teste ou devolver as filas ao Painel (seção 9).
2.1. **DSF, Certidões, Isenção DMAE e PRÓ-PÃO:** faltam o **deferimento** (quem pode deferir ainda não foi decidido) e os **PDFs** das fichas (os logos ficam para mais adiante, segundo o usuário). Falta confirmar se o Administrativo pode ver a lista do DSF, quem faz Certidões, Isenção DMAE e PRÓ-PÃO, quem escreve o parecer social (DMAE) e quem preenche a análise do sistema (PRÓ-PÃO).
2.2. **TAP 2026:** a planilha importada não tinha nenhum valor diário, só a linha TOTAL zerada.
3. **Backup do banco da VPS:** ainda não existe rotina. O Naicas tem uma (`backups/`, `instalar_auto_update.sh`), que pode servir de modelo.
4. **Paginação em `/atendimentos/`** (B6): com 675 registros a página tem 61 mil px e leva 1,6 s.
5. **Controle diário com dia cheio** (B12): a tabela estoura o card e o CPF e os nomes quebram em várias linhas.
6. **Registro inválido C1:** um `RegistroAtendimento` de importação com nome vazio. Decidir se apaga.
7. **Indicador "Atendidos"** (B9): decidir se conta os resolvidos na triagem.
8. **Atualização automática das filas** (B7), por exemplo recarregar a cada 30 s.

A configuração de produção (B2) foi feita em 26/11/2026: settings por ambiente, gunicorn, whitenoise e `compose.prod.yaml`.

## 13. Checklist ao terminar uma tarefa

- [ ] `.venv/Scripts/python manage.py test` passando, com testes novos para a regra nova.
- [ ] `.venv/Scripts/python manage.py makemigrations --check` sem pendências, e `migrate` aplicado.
- [ ] Commit e push (liberados, seção 7). Se a mudança vai para produção, depois o "Atualizar" da seção 7.1.
- [ ] Telas conferidas (screenshot) quando houver mudança visual.
- [ ] **Este CLAUDE.md atualizado** (regras, decisões, pendências, contagem de testes) e o MAPA, se for o caso.
- [ ] Nada de dado real ou segredo novo no que vai para o git.
