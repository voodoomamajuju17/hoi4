# 2100 Meganations — build
#
# Los .txt del mod son SALIDA del generador y no se editan a mano.
# Si cambia el lore, cambia spec/ y se regenera todo.
#
# Pasá tu instalación de HOI4 así (o exportá HOI4_PATH):
#   make build HOI4_PATH="/ruta/a/Hearts of Iron IV"

PY      ?= python3
OUT     ?= build
VANILLA := $(if $(HOI4_PATH),--vanilla-path "$(HOI4_PATH)",)

.PHONY: help validate build check install test clean all

help:
	@echo "make validate  — valida spec/ sin escribir nada"
	@echo "make build     — genera el mod en $(OUT)/"
	@echo "make check     — verifica que $(OUT)/ sea lo que produce spec/"
	@echo "make test      — corre los tests del generador"
	@echo "make install   — copia $(OUT)/ a la carpeta de mods de HOI4"
	@echo "make clean     — borra $(OUT)/"
	@echo ""
	@echo "HOI4_PATH=$(if $(HOI4_PATH),$(HOI4_PATH),(sin definir — las ideologias NO se generan))"

validate:
	@$(PY) -m tools.gen validate

build:
	@$(PY) -m tools.gen build --out $(OUT) $(VANILLA)

check:
	@$(PY) -m tools.gen check --out $(OUT) $(VANILLA)

install: build
	@$(PY) -m tools.gen install --out $(OUT) $(VANILLA)

test:
	@$(PY) -m tools.tests.test_gen

all: validate test build

clean:
	@rm -rf $(OUT)
	@echo "borrado $(OUT)/"
