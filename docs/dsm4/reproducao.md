# Reprodução do zero

Passo a passo para reproduzir tudo o que a entrega afirma, numa máquina limpa. Os tempos são os
medidos numa máquina de desenvolvimento (macOS, Apple Silicon) e servem de ordem de grandeza. Nada
usa a internet depois da instalação das dependências.

## 1. Pré-requisitos

| Ferramenta | Para quê | Obrigatória |
|---|---|---|
| Python 3.11 ou mais novo | sistema, testes, experimento, documentação | sim |
| git | gerador de números do relatório (lê a primeira rodada do experimento no histórico) | para o relatório |
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

## 3. Testes (cerca de 4 minutos)

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
python -m fin_mas experimento --replicas 30 --out docs/dsm4/resultados   # o experimento inteiro, cerca de 3 minutos (make experimento)
sha256sum docs/dsm4/resultados/execucoes.csv                             # shasum -a 256 no macOS
```

O SHA-256 do `execucoes.csv` tem de ser o de `docs/dsm4/resultados/manifesto.json`: o arquivo sai
idêntico byte a byte numa segunda execução. `tempo_parede.csv` muda a cada máquina e não entra em
nenhuma análise. O desenho está em {doc}`experimento` (pré-registro) e a leitura em {doc}`resultados`.

## 6. Documentação (cerca de 1 minuto)

```bash
python tools/trace.py                                          # regenera docs/_generated a partir de models/*.yaml
python -m sphinx -W --keep-going -b html docs docs/_build/html # make docs; sem avisos
```

## 7. Relatório, apresentação e pacote

```bash
python tools/relatorio_numeros.py --suite   # números do relatório (roda a suíte: cerca de 4 minutos; sem --suite, segundos)
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
