# SMA de Controladoria em contêiner (DSM4, docs/dsm4/implantacao.md).
#
#   docker compose up -d --build        (porta publicada só em 127.0.0.1:8765 do hospedeiro)
#
# Três estágios: (1) build do dashboard com bun; (2) wheel do fin-mas com os modelos YAML e o
# dashboard embutidos (tools/empacotar_wheel.py, o mesmo do `make wheel`); (3) runtime Python slim
# com o wheel instalado, usuário sem privilégios e healthcheck em /api/saude. Compatível com o
# builder clássico (sem recursos exclusivos do BuildKit).

FROM oven/bun:1.4.2 AS dashboard
WORKDIR /web
COPY web/package.json web/bun.lock ./
RUN bun install --frozen-lockfile
COPY web/ ./
RUN bun run build

FROM python:3.13-slim AS pacote
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
COPY models ./models
COPY tools/empacotar_wheel.py ./tools/empacotar_wheel.py
COPY --from=dashboard /web/dist ./web/dist
RUN python tools/empacotar_wheel.py --saida /wheel

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    FIN_MAS_DIR_CHAVES=/chaves
RUN useradd --system --uid 10001 --user-group --home-dir /home/sma --create-home sma \
 && mkdir -p /dados /chaves \
 && chown sma:sma /dados /chaves \
 && chmod 0700 /chaves
COPY --from=pacote /wheel/ /tmp/wheel/
RUN pip install --no-cache-dir /tmp/wheel/*.whl && rm -rf /tmp/wheel
COPY docker/entrada.sh /usr/local/bin/fin-mas-entrada
RUN chmod 0755 /usr/local/bin/fin-mas-entrada
USER sma
WORKDIR /home/sma
VOLUME ["/dados", "/chaves"]
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/api/saude', timeout=4).status == 200 else 1)"]
ENTRYPOINT ["fin-mas-entrada"]
CMD ["serve"]
