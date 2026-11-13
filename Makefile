PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
DSM1_DOC = entregas/dsm1/documentacao

.PHONY: all trace check docs pdf pdf-v2 test demo comparar experimento export serve web web-test modelos iniciar testes-tudo entrega-dsm2 entrega-dsm3 ataque clean \
	cenarios diagramas cobertura verificar-tudo

all: trace docs pdf

trace:
	$(PYTHON) tools/trace.py

check:
	$(PYTHON) tools/trace.py --check

docs: trace
	$(PYTHON) -m sphinx -W --keep-going -b html docs docs/_build/html

test:
	$(PYTHON) -m pytest

demo:
	PYTHONPATH=src $(PYTHON) -m fin_mas run --scenario fechar_mes --seed 42

comparar:
	PYTHONPATH=src $(PYTHON) -m fin_mas comparar --seeds 10 --out docs/dsm3/resultados

experimento:
	PYTHONPATH=src $(PYTHON) -m fin_mas experimento --replicas 30 --out docs/dsm4/resultados

export: comparar
	PYTHONPATH=src $(PYTHON) -m fin_mas export --out web/public/traces

modelos:
	PYTHONPATH=src $(PYTHON) -m fin_mas modelos --out modelos

web:
	cd web && bun install && bun run build

serve:
	PYTHONPATH=src $(PYTHON) -m fin_mas serve

iniciar:
	python3 tools/iniciar.py

testes-tudo:
	python3 tools/iniciar.py testes

entrega-dsm3:
	$(PYTHON) tools/empacotar_dsm3.py

ataque:
	mkdir -p saidas
	PYTHONPATH=src $(PYTHON) -m fin_mas run --scenario ataque_decisao_forjada --trace saidas/ataque.jsonl
	PYTHONPATH=src $(PYTHON) -m fin_mas verificar saidas/ataque.jsonl

entrega-dsm2:
	$(PYTHON) tools/empacotar_dsm2.py

web-test:
	cd web && bun run test && bun run test:e2e

# Catálogo de cenários rodado duas vezes por cenário, comparando os hashes dos traces
cenarios:
	PYTHONPATH=src $(PYTHON) -m fin_mas cenarios --verificar

# PNG dos .mmd da entrega DSM3 (Playwright + mermaid de web/node_modules; só os desatualizados)
diagramas:
	cd web && bun install && node ../tools/diagramas.mjs ../entregas/dsm3

# Cobertura da suíte pytest. Subprocessos da CLI (python -m fin_mas ...) não entram na medição.
cobertura:
	$(PYTHON) -m coverage run --source=src/fin_mas -m pytest -q
	$(PYTHON) -m coverage report --sort=cover

# Tudo o que a entrega promete, parando no primeiro erro; resumo de uma linha por etapa no final.
# Os comandos são os dos alvos check, test, cenarios, web-test e docs (sem $(MAKE) recursivo, para que
# `make -n verificar-tudo` só mostre o que faria).
verificar-tudo:
	@resumo=""; \
	etapa() { nome="$$1"; shift; echo "==> $$nome: $$*"; \
	  if sh -c "$$*"; then resumo="$$resumo\n  ok     $$nome"; \
	  else printf "\nResumo:$$resumo\n  FALHOU $$nome (as etapas seguintes não rodaram)\n"; exit 1; fi; }; \
	etapa check     "$(PYTHON) tools/trace.py --check"; \
	etapa test      "$(PYTHON) -m pytest"; \
	etapa cenarios  "PYTHONPATH=src $(PYTHON) -m fin_mas cenarios --verificar"; \
	etapa web-unit  "cd web && bun run test"; \
	etapa web-e2e   "cd web && bun run test:e2e"; \
	etapa docs      "$(PYTHON) tools/trace.py && $(PYTHON) -m sphinx -W --keep-going -b html docs docs/_build/html"; \
	printf "\nResumo:$$resumo\n"

pdf:
	cd $(DSM1_DOC) && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex && latexmk -c

pdf-v2:
	cd $(DSM1_DOC) && latexmk -pdf -interaction=nonstopmode -halt-on-error main-v2.tex && latexmk -c main-v2.tex

clean:
	rm -rf docs/_build
	cd $(DSM1_DOC) && latexmk -c
