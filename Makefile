PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
DSM1_DOC = entregas/dsm1/documentacao

.PHONY: all trace check docs pdf pdf-v2 test demo comparar export serve web web-test modelos iniciar testes-tudo clean

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
	PYTHONPATH=src $(PYTHON) -m fin_mas comparar --seeds 10 --out docs/dsm2/resultados

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

web-test:
	cd web && bun run test && bun run test:e2e

pdf:
	cd $(DSM1_DOC) && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex && latexmk -c

pdf-v2:
	cd $(DSM1_DOC) && latexmk -pdf -interaction=nonstopmode -halt-on-error main-v2.tex && latexmk -c main-v2.tex

clean:
	rm -rf docs/_build
	cd $(DSM1_DOC) && latexmk -c
