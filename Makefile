# Atalhos do projeto. Requer: Python 3.11+ (com as deps de docs/requirements.txt), Graphviz e TeX Live.
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: all trace check docs pdf clean

all: trace docs pdf

trace:            ## valida a cadeia e regenera docs/_generated, entregas/dsm1/generated e diagrams/dsm1/fsm_*.mmd
	$(PYTHON) tools/trace.py

check:            ## apenas valida a rastreabilidade (sem gerar arquivos)
	$(PYTHON) tools/trace.py --check

docs: trace       ## documentação HTML (falha com qualquer aviso)
	$(PYTHON) -m sphinx -W --keep-going -b html docs docs/_build/html

pdf: trace        ## PDF da entrega DSM1
	cd entregas/dsm1 && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex && latexmk -c

clean:
	rm -rf docs/_build
	cd entregas/dsm1 && latexmk -c
