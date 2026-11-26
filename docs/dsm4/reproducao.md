# Reprodução do zero

Passo a passo para reproduzir tudo o que a entrega afirma, numa máquina limpa. Os tempos são os
medidos numa máquina de desenvolvimento (macOS, Apple Silicon) e servem de ordem de grandeza. Nada
usa a internet depois da instalação das dependências.

## 1. Pré-requisitos

| Ferramenta | Para quê | Obrigatória |
|---|---|---|
| Python 3.11 ou mais novo | sistema, testes, experimento, documentação | sim |
| Graphviz (executável `dot` no PATH) | grafos do Sphinx | para o HTML |
| git | gerador de números do relatório (lê a primeira e a segunda rodada do experimento no histórico) | para o relatório |
| bun | dashboard (build, vitest, Playwright) | para o dashboard |
| Google Chrome (ou `PW_CHANNEL=chromium`) | roteiros Playwright e PNG dos diagramas | para o dashboard |
| TeX Live com `latexmk` e `rsvg-convert` (librsvg) | PDF do relatório | para o PDF |
| pandoc | `.pptx` da apresentação | para a apresentação |
| Docker | contêiner (opcional) | não |

## 2. Instalar (2 a 5 minutos)

```bash
git clone https://github.com/danrley-ribeiro/fin-dept-multiagents-project.git
cd fin-dept-multiagents-project
python3 -m venv .venv
.venv/bin/pip install -e . -r requirements-dev.txt -r docs/requirements.txt   # versões exatas: requirements-lock.txt
source .venv/bin/activate
export PYTHONPATH=src
```

Atalho: `./iniciar.sh instalar` (ou `.\iniciar.ps1 instalar` no Windows) faz o mesmo e prepara o
dashboard com o bun.

No ZIP extraído, entre em `codigo/` e comece pela criação do ambiente virtual. No Windows, ative com `.\.venv\Scripts\Activate.ps1` e use `python` nos comandos. O teste do wheel usa o backend de build já instalado por `requirements-dev.txt` e instala em um ambiente limpo sem consultar a rede. O histórico Git só é necessário para recuperar os números das rodadas anteriores ao regenerar as fontes do relatório.

## 3. Testes (de 5 a 15 minutos, conforme a máquina)

```bash
python -m pytest                       # suíte inteira, offline (unit, e2e, integração, TUI)
python tools/trace.py --check          # rastreabilidade: 0 erros, todos os requisitos com cadeia completa (segundos)
python -m fin_mas cenarios --verificar # cada cenário duas vezes: resposta explícita, invariantes, mesmo hash (segundos)
cd web && bun install && bun run test  # vitest (segundos)
bun run test:e2e                       # Playwright no Chrome, servidor Python real (alguns minutos)
cd ..
make verificar-tudo                    # tudo acima e a documentação, parando no primeiro erro
```

As contagens atuais (testes por pasta, cenários, objetos rastreados) estão no relatório e em
{doc}`cenarios-de-teste`, ambos gerados por `python tools/relatorio_numeros.py`.

## 4. Cenários e demonstração (segundos cada)

```bash
python -m fin_mas list                                  # catálogo
python -m fin_mas run --scenario veto_correcao          # trilha causal legível
python -m fin_mas run --scenario ataque_acesso          # ataques recusados
python -m fin_mas serve --demo                          # dashboard: http://127.0.0.1:8765, avaliador / Demonstracao-SMA-2026
```

Roteiro completo em {doc}`demonstracao`.

## 5. Experimento

```bash
python -m fin_mas experimento --rapido --out /tmp/experimento            # 3 seeds, cerca de 5 segundos
python -m fin_mas experimento --replicas 30 --out saidas/reproducao      # o experimento inteiro, cerca de 3 minutos (make experimento)
sha256sum saidas/reproducao/execucoes.csv                             # shasum -a 256 no macOS
```

A terceira rodada histórica permanece em `docs/dsm4/resultados/`. Para conferir a revisão final sem sobrescrever essa referência, use o destino `saidas/reproducao` indicado acima ou rode `make experimento`. Na CLI, explicite `--out` para preservar a pasta de resultados históricos. Duas execuções devem produzir o SHA-256 `b324fc61461ee3b88cb62eb69566c5588237a2257c5f6bca872b8675646c6102` para `execucoes.csv` (versão 1.1.0; a versão do pacote entra no trace e, por isso, no hash). O hash histórico é `9d5126a696cf421170d54616dab6f77e0c47c7e85dced5bc0e64c78a284bcae4`. O tempo de parede depende da máquina. No PowerShell, confira o CSV com `Get-FileHash saidas/reproducao/execucoes.csv`.

Para repetir os 240 pares do ensaio de carga, execute `python tools/estudo_carga.py saidas/reproducao/carga.csv` e compare o CSV com `docs/dsm4/resultados/carga.csv`. O desenho e as conclusões estão em {doc}`resultados`.

## 6. Documentação (cerca de 1 minuto)

```bash
python tools/trace.py                                          # regenera docs/_generated a partir de models/*.yaml
python -m sphinx -W --keep-going -b html docs docs/_build/html # make docs; sem avisos
```

## 7. Relatório, apresentação e pacote

```bash
python tools/relatorio_numeros.py --suite   # números do relatório (roda a suíte: cerca de 6 minutos; sem --suite, cerca de 20 s)
make pdf-dsm4                               # figuras SVG -> PDF (rsvg-convert) e latexmk: entregas/dsm4/documentacao/relatorio.pdf (cerca de 30 s)
make apresentacao-dsm4                      # slides.md -> DSM4-apresentacao.pptx com o tema da DSM2 (pandoc, segundos)
(cd web && node ../tools/diagramas.mjs ../entregas/dsm4)   # PNG dos .mmd da entrega (Playwright e mermaid do web/node_modules)
make entrega-dsm4                           # entregas/dsm4/DSM4-entrega.zip (segundos)
```

## 8. Contêiner (opcional, alguns minutos)

```bash
cp .env.example .env    # defina FIN_MAS_SENHA_NOVA, ou FIN_MAS_DEMO=1 só para avaliação
docker compose up -d --build
```

Detalhes e o que foi verificado em {doc}`implantacao`.
