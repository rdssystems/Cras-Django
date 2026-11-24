/* Gráficos do Painel (Apache ECharts 6).
   Os dados vêm prontos do Django em <script id="dados-graficos">, montados em cras/graficos.py. */
(function () {
    'use strict';

    var fonte = document.getElementById('dados-graficos');
    if (!fonte || !window.echarts) return;
    var DADOS = JSON.parse(fonte.textContent);

    // Paleta validada (contraste, croma e daltonismo) contra a superfície branca dos cards.
    // A ordem é a das camadas do gráfico empilhado: atendidos, resolvidos na triagem, sem atendimento.
    var SERIES = ['#2b3a8c', '#2e7a4c', '#c8471f'];
    var COR = {
        texto: '#1e2230',
        textoSec: '#454a5a',
        mudo: '#555b6b',
        grade: '#dfe2ec',
        eixo: '#dfe2ec',
        superficie: '#ffffff',
        faixa: 'rgba(100, 116, 139, 0.08)'
    };
    var FONTE = "Lexend, system-ui, -apple-system, 'Segoe UI', sans-serif";
    // O ECharts mede os rótulos do eixo (para reservar espaço) sem herdar a fonte global;
    // sem a fonte em cada rótulo, ele mede numa fonte mais estreita e o texto sai cortado.
    function texto(estilo, extra) { return Object.assign({ fontFamily: FONTE }, estilo, extra); }
    var numero = new Intl.NumberFormat('pt-BR');
    var esc = echarts.format.encodeHTML;

    function unidade(g, n) { return n === 1 ? g.unidade[0] : g.unidade[1]; }
    function rotuloDe(g, i) { return g.dicas ? g.dicas[i] : g.categorias[i]; }
    function maiuscula(texto) { return texto.charAt(0).toUpperCase() + texto.slice(1); }

    // ---------------------------------------------------------------- dica (tooltip)
    // O valor vem primeiro e em destaque; o nome vem depois, mais discreto.
    function cabecalhoDica(titulo) {
        return '<div class="dica-titulo">' + esc(titulo) + '</div>';
    }
    function linhaDica(cor, valor, nome) {
        return '<div class="dica-linha">' +
            (cor ? '<span class="dica-chave" style="background:' + cor + '"></span>' : '') +
            '<strong>' + numero.format(valor) + '</strong><span>' + esc(nome) + '</span></div>';
    }

    // ---------------------------------------------------------------- peças comuns
    function base(g) {
        return {
            animationDuration: 450,
            textStyle: { fontFamily: FONTE, color: COR.textoSec },
            grid: { left: 4, right: 12, top: 16, bottom: 4, containLabel: true },
            tooltip: {
                trigger: 'axis',
                confine: true,
                backgroundColor: COR.superficie,
                borderColor: '#dfe2ec',
                borderWidth: 1,
                padding: [8, 12],
                textStyle: { fontFamily: FONTE, color: COR.texto, fontSize: 13 },
                extraCssText: 'border-radius:10px;box-shadow:0 8px 24px rgba(15,23,42,.12);',
                axisPointer: { type: 'shadow', shadowStyle: { color: COR.faixa } },
                formatter: function (params) {
                    var p = params[0];
                    return cabecalhoDica(rotuloDe(g, p.dataIndex)) + linhaDica(null, p.value, unidade(g, p.value));
                }
            }
        };
    }

    function eixoCategorias(g, extra) {
        return Object.assign({
            type: 'category',
            data: g.categorias,
            axisTick: { show: false },
            axisLine: { lineStyle: { color: COR.eixo } },
            axisLabel: texto({ color: COR.mudo, fontSize: 12 })
        }, extra || {});
    }

    function eixoValores() {
        return {
            type: 'value',
            minInterval: 1,
            splitLine: { lineStyle: { color: COR.grade, width: 1, type: 'solid' } },
            axisLabel: texto({ color: COR.mudo, fontSize: 12, formatter: function (v) { return numero.format(v); } })
        };
    }

    function rotuloValor(extra) {
        return texto({
            show: true,
            color: COR.textoSec,
            fontSize: 12,
            fontWeight: 600,
            formatter: function (p) { return numero.format(p.value); }
        }, extra);
    }

    var DESTAQUE = { itemStyle: { opacity: 0.82 } };

    // ---------------------------------------------------------------- tipos de gráfico

    // Colunas de uma série. Com poucas colunas o valor vai no topo de cada uma e o eixo Y some;
    // com muitas, o eixo fica e só o pico ganha rótulo.
    function colunas(g) {
        var o = base(g);
        var valores = g.series[0].valores;
        var poucas = valores.length <= 8;
        var maior = Math.max.apply(null, valores);
        o.grid.top = 28;
        o.xAxis = eixoCategorias(g);
        // Eixo escondido: o máximo é o dado (e não um número "redondo"), para não sobrar vão em cima.
        o.yAxis = poucas ? { type: 'value', show: false, max: 'dataMax' } : eixoValores();
        o.series = [{
            type: 'bar',
            data: valores,
            barMaxWidth: 24,
            itemStyle: { color: SERIES[0], borderRadius: [4, 4, 0, 0] },
            emphasis: DESTAQUE,
            label: rotuloValor({
                position: 'top',
                formatter: function (p) {
                    return p.value && (poucas || p.value === maior) ? numero.format(p.value) : '';
                }
            })
        }];
        return o;
    }

    // Barras horizontais em ranking (maior em cima), valor na ponta, sem eixo de valores.
    // No celular o rótulo encolhe (com reticências) para sobrar espaço para a barra.
    function barras(g, largura) {
        var o = base(g);
        o.grid = { left: 4, right: 56, top: 4, bottom: 4, containLabel: true };
        o.yAxis = eixoCategorias(g, {
            inverse: true,
            axisLine: { show: false },
            axisLabel: texto({
                color: COR.texto, fontSize: 12.5, overflow: 'truncate', margin: 12,
                width: Math.min(210, Math.round(largura * 0.42))
            })
        });
        o.xAxis = { type: 'value', show: false, max: 'dataMax' };
        o.series = [{
            type: 'bar',
            // Zero fica em cinza-claro: a categoria aparece, mas não compete com quem tem valor.
            data: g.series[0].valores.map(function (v) {
                return v ? v : { value: v, label: { color: COR.mudo, fontWeight: 400 } };
            }),
            barMaxWidth: 18,
            itemStyle: { color: SERIES[0], borderRadius: [0, 4, 4, 0] },
            emphasis: DESTAQUE,
            label: rotuloValor({ position: 'right', distance: 8 })
        }];
        return o;
    }

    // Série temporal: linha de 2px com área bem suave e o pico rotulado.
    function area(g) {
        var o = base(g);
        var cor = SERIES[0];
        o.grid.top = 32;
        o.tooltip.axisPointer = { type: 'line', lineStyle: { color: COR.eixo, width: 1 } };
        o.xAxis = eixoCategorias(g, { boundaryGap: false });
        o.yAxis = eixoValores();
        o.series = [{
            type: 'line',
            data: g.series[0].valores,
            smooth: 0.3,
            smoothMonotone: 'x',
            showSymbol: false,
            symbol: 'circle',
            symbolSize: 8,
            lineStyle: { width: 2, color: cor, cap: 'round', join: 'round' },
            itemStyle: { color: cor, borderColor: COR.superficie, borderWidth: 2 },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(43, 58, 140, 0.16)' },
                    { offset: 1, color: 'rgba(43, 58, 140, 0.02)' }
                ])
            },
            emphasis: { focus: 'none', scale: false },
            markPoint: {
                symbol: 'circle',
                symbolSize: 8,
                itemStyle: { color: cor, borderColor: COR.superficie, borderWidth: 2 },
                label: rotuloValor({ position: 'top', distance: 6, color: COR.texto }),
                data: [{ type: 'max' }]
            }
        }];
        return o;
    }

    // Colunas empilhadas por desfecho. Uma dica lista todas as camadas do dia, mais o total.
    function colunasEmpilhadas(g) {
        var o = base(g);
        var topo = g.categorias.map(function (_, i) {
            var k = -1;
            g.series.forEach(function (s, j) { if (s.valores[i]) k = j; });
            return k;
        });
        o.grid.top = 44;
        o.legend = {
            top: 0,
            left: 0,
            selectedMode: false,
            icon: 'roundRect',
            itemWidth: 12,
            itemHeight: 12,
            itemGap: 20,
            textStyle: texto({ color: COR.textoSec, fontSize: 12.5 }),
            data: g.series.map(function (s) { return s.nome; })
        };
        o.xAxis = eixoCategorias(g);
        o.yAxis = eixoValores();
        o.tooltip.formatter = function (params) {
            var total = 0;
            var linhas = params.map(function (p) {
                total += p.value;
                return linhaDica(p.color, p.value, p.seriesName);
            }).join('');
            return cabecalhoDica(rotuloDe(g, params[0].dataIndex)) + linhas +
                '<div class="dica-total"><strong>' + numero.format(total) + '</strong> ' +
                esc(unidade(g, total)) + '</div>';
        };
        o.series = g.series.map(function (s, k) {
            return {
                name: s.nome,
                type: 'bar',
                stack: 'total',
                barMaxWidth: 20,
                // A borda na cor da superfície é o respiro de 2px entre as camadas.
                itemStyle: { color: s.cor || SERIES[k], borderColor: COR.superficie, borderWidth: 1 },
                emphasis: DESTAQUE,
                data: s.valores.map(function (v, i) {
                    // Só a camada de cima de cada coluna tem o topo arredondado.
                    return topo[i] === k ? { value: v, itemStyle: { borderRadius: [4, 4, 0, 0] } } : v;
                })
            };
        });
        return o;
    }

    var MONTAR = { colunas: colunas, barras: barras, area: area, colunas_empilhadas: colunasEmpilhadas };

    // ---------------------------------------------------------------- tabela (mesmos dados, sem gráfico)
    function celula(linha, texto, numerica, tag) {
        var c = document.createElement(tag || 'td');
        c.textContent = texto;
        if (numerica) c.className = 'num';
        linha.appendChild(c);
    }

    function montarTabela(g, destino) {
        var varias = g.series.length > 1;
        var tabela = document.createElement('table');
        tabela.className = 'tabela';

        var cabecalho = tabela.createTHead().insertRow();
        celula(cabecalho, g.eixo, false, 'th');
        if (varias) {
            g.series.forEach(function (s) { celula(cabecalho, s.nome, true, 'th'); });
            celula(cabecalho, 'Total', true, 'th');
        } else {
            celula(cabecalho, maiuscula(g.unidade[1]), true, 'th');
        }

        var corpo = tabela.createTBody();
        g.categorias.forEach(function (_, i) {
            var linha = corpo.insertRow();
            var total = 0;
            celula(linha, rotuloDe(g, i));
            g.series.forEach(function (s) {
                total += s.valores[i];
                celula(linha, numero.format(s.valores[i]), true);
            });
            if (varias) celula(linha, numero.format(total), true);
        });
        destino.appendChild(tabela);
    }

    // ---------------------------------------------------------------- montagem
    function desenhar() {
        document.querySelectorAll('[data-grafico]').forEach(function (el) {
            var g = DADOS[el.dataset.grafico];
            if (!g || !MONTAR[g.tipo]) return;
            if (g.tipo === 'barras') {
                // Altura pela quantidade de linhas (lista curta ganha linhas mais folgadas); o CSS centraliza no card.
                var linha = g.categorias.length <= 5 ? 44 : 34;
                el.style.height = Math.max(160, g.categorias.length * linha + 16) + 'px';
            }
            var grafico = echarts.init(el, null, { renderer: 'svg' });
            grafico.setOption(MONTAR[g.tipo](g, el.clientWidth));

            var redimensionar = function () {
                if (el.clientWidth) grafico.resize();
            };
            if (window.ResizeObserver) {
                new ResizeObserver(redimensionar).observe(el);
            } else {
                window.addEventListener('resize', redimensionar);
            }
        });
    }

    // O ECharts mede os rótulos ao desenhar: esperar a Inter carregar evita rótulo cortado.
    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(desenhar);
    } else {
        desenhar();
    }

    document.querySelectorAll('[data-alternar-tabela]').forEach(function (botao) {
        botao.addEventListener('click', function () {
            var card = botao.closest('.grafico-card');
            var el = card.querySelector('[data-grafico]');
            var destino = card.querySelector('.grafico-tabela');
            if (!destino.firstChild) montarTabela(DADOS[el.dataset.grafico], destino);

            var mostrar = !card.classList.contains('mostrar-tabela');
            card.classList.toggle('mostrar-tabela', mostrar);
            botao.setAttribute('aria-pressed', String(mostrar));
            botao.title = mostrar ? 'Ver como gráfico' : 'Ver como tabela';
            botao.querySelector('.material-symbols-outlined').textContent = mostrar ? 'bar_chart' : 'table_rows';
        });
    });
})();
