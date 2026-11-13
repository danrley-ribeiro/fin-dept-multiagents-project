#!/bin/sh
# Entrada do contêiner (DSM4). `serve` (padrão): na primeira subida roda o assistente de instalação na
# pasta de dados (/dados) e depois sobe o servidor escutando em 0.0.0.0 DENTRO do contêiner. O Docker
# publica a porta só em 127.0.0.1 do hospedeiro e o servidor continua aceitando só Host/Origin de
# loopback: o navegador entra por http://localhost:8765. Qualquer outro comando vai direto ao fin-mas
# (ex.: `docker compose run --rm sma doctor --pasta /dados`).
set -eu
PASTA=/dados
export FIN_MAS_DIR_CHAVES="${FIN_MAS_DIR_CHAVES:-/chaves}"   # .env com o valor vazio não tira as chaves do volume

if [ "${1:-serve}" != "serve" ]; then
  exec fin-mas "$@"
fi

if [ ! -f "$PASTA/instalacao.json" ]; then
  if [ "${FIN_MAS_DEMO:-0}" = "1" ]; then
    fin-mas instalar --pasta "$PASTA" --demo --porte "${FIN_MAS_PORTE:-media}" \
      --segmento "${FIN_MAS_SEGMENTO:-software_servicos}" --cognicao "${FIN_MAS_COGNICAO:-local}"
  else
    # sem terminal: a senha do administrador vem de FIN_MAS_SENHA_NOVA (tire-a do .env depois da 1ª subida)
    fin-mas instalar --pasta "$PASTA" --usuario "${FIN_MAS_ADMIN:-admin}" --porte "${FIN_MAS_PORTE:-media}" \
      --segmento "${FIN_MAS_SEGMENTO:-software_servicos}" --cognicao "${FIN_MAS_COGNICAO:-local}"
  fi
fi
exec fin-mas serve --instalacao "$PASTA" --host 0.0.0.0 --porta 8765
