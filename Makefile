PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
DSM1_DOC = entregas/dsm1/documentacao

.PHONY: all trace check docs pdf clean

all: trace docs pdf

trace:
	$(PYTHON) tools/trace.py

check:
	$(PYTHON) tools/trace.py --check

docs: trace
	$(PYTHON) -m sphinx -W --keep-going -b html docs docs/_build/html

pdf:
	cd $(DSM1_DOC) && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex && latexmk -c

clean:
	rm -rf docs/_build
	cd $(DSM1_DOC) && latexmk -c
