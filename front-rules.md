# Padrão de dashboards dos sistemas da Secretaria

**Manual de interface e implementação · Referência visual do Naicas**

Quem muda de sistema deve continuar reconhecendo onde está, quais dados está consultando e como iniciar uma tarefa. O dashboard é a principal aplicação deste padrão. Cadastros, consultas e relatórios herdam a mesma identidade, com uma composição própria para cada tarefa.

## Como usar

Para iniciar um painel, preencha a ficha da seção 8 com a equipe responsável pelo serviço. Monte a primeira tela com as decisões mais frequentes daquele público. Antes da entrega, percorra os cenários da seção 9 com um perfil que opere o sistema e outro com acesso restrito.

## Sumário navegável

1. [Estrutura comum](#1-estrutura-comum)
2. [Identidade visual](#2-identidade-visual)
3. [Anatomia do dashboard](#3-anatomia-do-dashboard)
4. [Indicadores, filtros e estados](#4-indicadores-filtros-e-estados)
5. [Responsividade e acessibilidade](#5-responsividade-e-acessibilidade)
6. [Aplicação nas demais telas](#6-aplicação-nas-demais-telas)
7. [Implementação de referência em Django](#7-implementação-de-referência-em-django)
8. [Ficha de adoção por sistema](#8-ficha-de-adoção-por-sistema)
9. [Critérios de aceite](#9-critérios-de-aceite)

## 1 Estrutura comum

| Camada | O que é compartilhado | O que cada sistema define |
| --- | --- | --- |
| Secretaria | Paleta, fonte, hierarquia, estilos de ação, mensagens e comportamento responsivo. | Nome do sistema e arquivos oficiais de identificação aplicáveis. |
| Navegação | Barra superior com identificação, acesso aos módulos e contexto ativo. Cabeçalho com um título principal. | Módulos disponíveis, seus destinos e o recorte de trabalho, como unidade, setor ou território. |
| Dashboard | Ordem de leitura, componentes de indicador, filtro, lista e gráfico, e tratamento dos estados da consulta. | Perguntas de gestão, dados, períodos, metas, prioridades e ações. |
| Operação | Padrões de formulário, tabela, confirmação e retorno após uma ação. | Campos, validações de negócio, permissões e regras de histórico. |

Preserve os arquivos oficiais de marca, ícone e favicon de cada sistema. No Naicas, conserve também a fita de identificação da unidade. Nos demais sistemas, use a mesma posição de contexto quando unidade, setor ou território alterar o significado dos dados. Se houver apenas um contexto, apresente seu nome como texto.

## 2 Identidade visual

Use a paleta e a tipografia do Naicas como padrão comum. Mantenha as definições na folha de estilos da base. Cada módulo consome os tokens pelo papel que desempenham na interface.

| Papel | Token CSS sugerido | Referência | Aplicação |
| --- | --- | --- | --- |
| Primária | `--cor-primaria` | `#2b3a8c` · anil | Navegação, links e ação principal. |
| Primária escura | `--cor-primaria-escura` | `#1f2a6b` | Extremidade escura do gradiente de cabeçalho. |
| Atenção crítica | `--cor-critica` | `#c8471f` · urucum | Falha, pendência crítica e ação destrutiva identificada por texto. |
| Atenção | `--cor-atencao` | `#f2b705` · ipê | Alerta que pede acompanhamento. Use texto grafite sobre o amarelo. |
| Sucesso | `--cor-sucesso` | `#2e7a4c` · folha | Confirmação de operação e situação regular. |
| Fundo | `--cor-fundo` | `#f3f4f8` · papel | Fundo da página entre os componentes. |
| Texto | `--cor-texto` | `#1e2230` · grafite | Títulos, valores e conteúdo. |
| Borda | `--cor-borda` | `#dfe2ec` | Contorno de cards, divisórias e separação de superfícies. |

**Tipografia e forma.** Use Lexend no corpo, tamanho de `0.9375rem`, entrelinha de `1.55` e peso `600` nos cabeçalhos. Adote espaçamentos da escala Bootstrap, cantos de `0.5rem` a `0.75rem` e sombras discretas. Rótulos secundários têm menor destaque que o valor ou título a que se referem.

**Cabeçalhos e ações.** Reaproveite `cabecalho-pagina` no painel e nas páginas internas. Destaque uma ação principal em anil. Use contorno nas secundárias, verbos específicos nos rótulos e confirmação para exclusão. Cor, ícone e texto devem comunicar o mesmo estado. Para um serviço novo, comece pela base compartilhada e identifique o serviço pelo nome e pela marca existente.

## 3 Anatomia do dashboard

A primeira leitura responde a três perguntas. **Qual é a situação agora? O que exige atenção? Onde posso agir?** Use a seguinte ordem de referência. O índice acompanha o conteúdo efetivamente exibido.

| Posição | Bloco | Regra de composição |
| --- | --- | --- |
| Topo | Barra compartilhada | Identifique o sistema e o contexto ativo. Ofereça a navegação principal disponível para o perfil. |
| Abertura | Cabeçalho contextual | Um título, período ou recorte que explique os dados e até três ações prioritárias. Exemplo de ação principal em Frota — “Registrar saída”. |
| Ao lado do conteúdo no desktop | Índice de seções | Use em painéis com várias seções. Os rótulos e destinos correspondem aos títulos visíveis. Um painel curto pode dispensar o índice. |
| Primeira faixa do conteúdo | Indicadores | Priorize as decisões mais frequentes. Cada card apresenta rótulo, valor, unidade quando aplicável e recorte. Coloque um link se houver uma consulta correspondente. |
| Após o resumo | Filtros e resultados | Agrupe os filtros combináveis e mostre quais estão ativos. Apresente a lista ou tabela com total, paginação quando necessária e acesso ao detalhe. |
| Operação diária | Fila de trabalho | Inclua quando existir uma rotina acionável. Cada item identifica a pendência, seu estado e a próxima ação permitida. |
| Análise | Gráfico e tabela equivalente | Inclua quando uma tendência ou comparação apoiar uma decisão. Identifique o período e ofereça os mesmos valores em tabela. |
| Complemento | Seções de domínio | Adicione blocos como unidades, veículos ou solicitações quando responderem a outra pergunta relevante para aquele perfil. |

**Exemplo de percurso.** Em Frota, a pessoa responsável vê o card “Veículos em uso”, abre a lista das saídas em aberto na unidade atual e seleciona uma delas para registrar o retorno. O link do card leva consigo a unidade e a situação “Em uso”. Depois da confirmação, a lista e o indicador passam a refletir o retorno.

## 4 Indicadores, filtros e estados

Para cada indicador, registre a pergunta atendida, a fonte, a regra de cálculo, a unidade de medida, o período, os filtros aplicáveis e o destino de detalhamento. Se houver meta, identifique quem a definiu e para qual período vale. Nos indicadores percentuais, explicite numerador, denominador e tratamento de denominador zero.

**Filtros e escopo.** Mostre o recorte perto dos números. Ao aplicar um novo filtro, volte à primeira página. Ao paginar ou abrir o detalhamento, preserve os critérios relevantes. Se uma fila ou um card usar período diferente do filtro geral, rotule o seu recorte junto ao título. Por exemplo, um card “Em uso agora” continua indicando o estado atual quando a tabela abaixo consulta o histórico do mês.

| Estado | Como apresentar | Exemplo |
| --- | --- | --- |
| Zero apurado | Exibir o número e a unidade. | “0 solicitações pendentes”. |
| Dado ausente ou cálculo indefinido | Exibir travessão com explicação. Interromper a série quando faltar uma observação. | “— · Sem chamadas registradas no período”. |
| Consulta válida sem resultados | Conservar a seção de resultados, explicar o recorte e oferecer ajuste dos filtros. | “Nenhum veículo atende aos filtros selecionados.” |
| Filtro inválido | Preservar as entradas, identificar o campo e suspender os resultados dependentes até a correção. | “A data final deve ser igual ou posterior à inicial.” |
| Acesso restrito | Verificar o acesso no servidor, inclusive ao abrir uma URL diretamente. No painel, exibir as operações permitidas. | Consulta disponível para leitura, edição restrita ao perfil responsável. |
| Falha de atualização | Identificar o bloco afetado e oferecer nova tentativa quando possível. | “Não foi possível carregar as solicitações.” |

O índice e a respectiva seção usam a mesma condição de exibição. Uma fila vazia pode continuar visível com “Nenhuma pendência” quando esse resultado confirma à equipe que a rotina está em dia.

## 5 Responsividade e acessibilidade

| Largura da tela | Índice e conteúdo | Indicadores e ações |
| --- | --- | --- |
| A partir de 1200 px | Índice lateral de `11.5rem` quando presente. | Até quatro indicadores por linha. |
| 992 a 1199 px | Índice lateral de `10rem`. | Duas colunas de indicadores. |
| 576 a 991 px | Uma coluna principal com índice horizontal de rolagem própria. | Cards se reorganizam conforme o espaço para rótulos e valores. |
| Abaixo de 576 px | Cabeçalho compacto, índice horizontal quando presente e avatar decorativo oculto. | Priorize uma coluna para cards largos. Botões com altura mínima de `2.75rem`. |

- Use `minmax(0, 1fr)` na coluna principal do grid e `min-width: 0` em seus itens. Restrinja a rolagem horizontal à tabela, gráfico ou índice que dela precisar.
- Garanta um título principal, subtítulos em ordem, rótulos associados aos campos e cabeçalhos nas tabelas. Mantenha o foco visível e o percurso de teclado na ordem de leitura.
- Dê nome acessível a botões de ícone e marque ícones decorativos com `aria-hidden="true"`. Exiba mensagens de erro junto aos campos e associe-as ao controle.
- Verifique o contraste das combinações reais de texto e fundo, inclusive nos estados de foco. Gráficos oferecem tabela equivalente e qualquer dica interativa deve funcionar por teclado e toque.

## 6 Aplicação nas demais telas

| Tela | Elementos que herda do painel | Composição própria |
| --- | --- | --- |
| Listagem e consulta | Barra, cabeçalho, filtros, tabela e estados de resultado. | Título da coleção, ação de cadastro quando permitida, busca, paginação e acesso ao detalhe. |
| Detalhe | Cabeçalho contextual, tipografia, estados e hierarquia de ações. | Identificação do registro, situação atual, dados agrupados e operações permitidas. |
| Cadastro e edição | Barra, cabeçalho, campos, mensagens e botões. | Grupos de campos em ordem de preenchimento, ação “Salvar”, retorno e indicação de erros. Preserve os valores após validação. |
| Relatório | Filtros, tabelas, títulos e convenções de gráficos. | Identificação do período, escopo e unidade de medida. Se existir exportação, aplique o mesmo recorte e as mesmas permissões. |

Um formulário simples pode ter apenas cabeçalho, campos e ações. Cards de indicadores, índice de seções e gráficos entram nas telas em que ajudam a executar a tarefa.

## 7 Implementação de referência em Django

Para projetos Django, use Django Templates, Bootstrap 5.3 e Bootstrap Icons conforme a referência do Naicas. Em outra tecnologia, preserve a organização visual, as regras de interação e os limites de acesso. Os nomes abaixo são sugestões para um projeto novo.

| Local de referência | Responsabilidade |
| --- | --- |
| `core/templates/core/base.html` e `core/static/core/` | Marca, favicon, Lexend, tokens, navegação, mensagens e estilos de componentes compartilhados. |
| `dashboard/views.py` | Verificar acesso ao painel, obter o contexto autorizado, validar os filtros e compor a resposta. |
| `dashboard/filtros.py` e `dashboard/indicadores.py` | Validar os critérios e calcular agregações sobre o conjunto de dados autorizado. |
| `dashboard/templates/dashboard/painel.html` e parciais | Estender a base, renderizar as seções e gerar o índice a partir das seções visíveis. |
| `dashboard/static/dashboard/` | Grid, comportamento responsivo e interações específicas do painel. |
| Apps de domínio | Manter consultas de negócio, cadastros, edição e histórico na funcionalidade responsável. |

**Contrato do painel.** A view entrega título, contexto ativo, período, filtros e erros, indicadores, resultados paginados, seções visíveis, séries de dados e ações autorizadas. Forme a consulta a partir do escopo da pessoa usuária e aplique os filtros validados antes de agregar. Resolva os destinos com `reverse` ou com a tag `url`. Use os mesmos dados para desenhar o gráfico e montar sua tabela.

| Interação | Comportamento |
| --- | --- |
| Consultar, filtrar ou paginar | GET com parâmetros validados. A paginação altera apenas o número da página. |
| Trocar unidade de trabalho salva na sessão | POST com CSRF. Valide a unidade permitida e qualquer destino de retorno. |
| Cadastrar, editar, concluir ou excluir | POST com CSRF e autorização da operação sobre o registro. Exclusões exigem confirmação explícita. |

Carregue o JavaScript próprio com `defer` e inicialize cada componente apenas quando ele estiver presente. Reaproveite o CSS existente do Naicas ao adotar o padrão nesse sistema.

## 8 Ficha de adoção por sistema

Copie a coluna “Preencher” para a especificação do projeto. Os exemplos ilustram escolhas possíveis e devem ser confirmados com a equipe de cada serviço.

| Decisão | Preencher | Exemplo · Matrículas | Exemplo · Frota |
| --- | --- | --- | --- |
| Público e escopo | [Quem usa e quais registros pode consultar?] | Coordenação da unidade selecionada. | Responsável pelos veículos da unidade selecionada. |
| Pergunta do painel | [Que decisão deve ser tomada?] | Quais matrículas precisam de conferência? | Quais veículos ainda estão em uso? |
| Indicador e fonte | [Rótulo, fonte, cálculo e unidade] | “Aguardando conferência”. Contar matrículas distintas nessa situação no cadastro. | “Veículos em uso”. Contar veículos distintos com saída em aberto no controle de movimentações. |
| Tempo e ausência | [Data de referência e regra para zero ou ausência] | Situação atual. Consulta válida sem pendências exibe 0. | Situação atual. Fonte indisponível exibe falha de atualização. |
| Filtros e detalhe | [Quais critérios e qual lista explicam o número?] | Unidade e turno. Abrir a lista com a situação já aplicada. | Unidade e situação. Abrir a lista de saídas em aberto. |
| Rotina e ação | [Quem pode agir, em qual tela e com que resultado?] | Pessoa autorizada abre a matrícula pendente e registra a conferência. | Pessoa autorizada abre a saída selecionada e registra o retorno. |
| Análise opcional | [Qual comparação apoia uma decisão?] | Entradas por mês para planejar a conferência. | Saídas por semana para planejar a disponibilidade. |

**Instrução reutilizável para a equipe**

> Implemente o dashboard de [sistema] com a base visual compartilhada da Secretaria e os componentes deste manual. O público é [perfis] e o escopo de trabalho é [recorte]. O painel deve ajudar a decidir [decisão]. Use os indicadores [cálculos e fontes], os filtros [critérios] e as ações [rótulos e destinos]. Inclua [seções necessárias]. Preserve o recorte ao abrir o detalhamento e valide os cenários de aceite abaixo.

## 9 Critérios de aceite

| Verificação | Resultado esperado |
| --- | --- |
| Identidade entre sistemas | Em dois painéis lado a lado, fonte, cores, cabeçalhos, filtros e hierarquia de botões seguem a mesma base. O nome distingue os serviços. |
| Indicador e detalhamento | Para o mesmo perfil, período e filtros, o número pode ser reproduzido na consulta de origem pela regra de cálculo documentada. |
| Filtros e paginação | Combinar critérios altera os resultados. Mudar de página mantém o recorte. Uma entrada inválida apresenta erro e conserva os valores digitados. |
| Permissão e contexto | Testar ao menos dois perfis e, quando aplicável, duas unidades. Uma URL direta com unidade ou registro fora do escopo mantém a restrição de acesso. |
| Ações e navegação | Links levam a rotas existentes. Âncoras têm destinos únicos e visíveis. Alterações validam método, permissão e CSRF. |
| Estados e gráficos | Zero, dado ausente e consulta vazia são distinguíveis. Gráfico e tabela coincidem em período, valores, lacunas e unidade. |
| Revisão no navegador | Conferir 375, 768 e 1440 px. Cabeçalho, cards e ações permanecem legíveis. Percorrer filtro, resultado e ação por teclado e verificar as marcas e os ícones. |
| Telas internas | Abrir uma listagem, um detalhe e um formulário a partir do painel. O contexto é identificável durante todo o percurso. |

Em Django, cubra filtros, escopo, paginação e mutações com o cliente de testes, incluindo `enforce_csrf_checks=True` nos cenários de CSRF. Para alinhamento, foco e rolagem, faça a conferência no navegador.

*Referência de origem: “Padrão de dashboards para projetos Django”, baseado na interface do Naicas aprovada em 05/11/2026. Os exemplos de adoção acima descrevem possibilidades de aplicação do padrão.*
