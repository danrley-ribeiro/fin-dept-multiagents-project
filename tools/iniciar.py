#!/usr/bin/env python3
"""Um comando para tudo: prepara o ambiente e executa o projeto no modo escolhido.

    python tools/iniciar.py [modo] [--porta 8765] [--sem-navegador]

Modos:
    ao-vivo   (padrão) escritório com os agentes executando agora: servidor + dashboard
    replay    dashboard sem servidor, reproduzindo os traces exportados (offline)
    dev       servidor Python + Vite em modo desenvolvimento (recarga automática)
    testes    pytest (e2e e integração), rastreabilidade, testes do dashboard e de uso real
    docs      gera a documentação (Sphinx) em docs/_build/html
    cli       roda um cenário no terminal (use --cenario e --porte)
    instalar  só prepara o ambiente

O que é preparado (só quando falta ou mudou): Python 3.11+ (verificado), ambiente virtual
.venv com as dependências do projeto, bun (instalado pelo instalador oficial se não
existir), dependências do dashboard, build do dashboard e traces do replay offline.
Usa só a biblioteca padrão, para rodar antes de existir o .venv.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "web"
VENV = RAIZ / ".venv"
WINDOWS = os.name == "nt"
PY_VENV = VENV / ("Scripts/python.exe" if WINDOWS else "bin/python")
MODOS = ("ao-vivo", "replay", "dev", "testes", "docs", "cli", "instalar")


def passo(texto):
    print(f"\n==> {texto}", flush=True)


def rodar(cmd, cwd=RAIZ, **kw):
    print("   $ " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=_env(), check=kw.pop("check", True), **kw)


def _env():
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": str(RAIZ / "src")}
    bun_dir = Path.home() / ".bun" / "bin"
    env["PATH"] = os.pathsep.join([str(bun_dir), env.get("PATH", "")])
    return env


def _hash(*arquivos) -> str:
    h = hashlib.sha256()
    for a in arquivos:
        p = RAIZ / a
        h.update(p.read_bytes() if p.exists() else b"")
    return h.hexdigest()


def _mais_novo(pasta: Path, sufixos) -> float:
    return max((p.stat().st_mtime for p in pasta.rglob("*") if p.suffix in sufixos), default=0.0)


# ---------------------------------------------------------------- preparação
def verificar_python():
    if sys.version_info < (3, 11):
        sys.exit(f"Python 3.11+ é necessário (encontrado {sys.version.split()[0]}). "
                 "Use ./iniciar.ps1 (Windows) ou ./iniciar.sh, que instalam/indicam o Python certo.")


def preparar_python(docs=False):
    if not PY_VENV.exists():
        passo("Criando o ambiente virtual .venv")
        rodar([sys.executable, "-m", "venv", VENV])
    marca, atual = VENV / ".sma-deps", _hash("pyproject.toml", "requirements-dev.txt")
    if not marca.exists() or marca.read_text() != atual:
        passo("Instalando as dependências Python (projeto e testes)")
        rodar([PY_VENV, "-m", "pip", "install", "-q", "--upgrade", "pip"])
        rodar([PY_VENV, "-m", "pip", "install", "-q", "-e", ".", "-r", "requirements-dev.txt"])
        marca.write_text(atual)
    else:
        passo("Dependências Python já instaladas")
    if docs:  # Sphinx 9 exige Python 3.12+; os demais modos funcionam com 3.11
        versao = subprocess.run([PY_VENV, "-c", "import sys; print(sys.version_info >= (3, 12))"],
                                capture_output=True, text=True).stdout.strip()
        if versao != "True":
            sys.exit("O modo docs exige Python 3.12+ no .venv (Sphinx 9). Recrie o .venv com Python 3.12 "
                     "ou mais novo; os demais modos funcionam com 3.11.")
        marca, atual = VENV / ".sma-deps-docs", _hash("docs/requirements.txt")
        if not marca.exists() or marca.read_text() != atual:
            passo("Instalando as dependências da documentação")
            rodar([PY_VENV, "-m", "pip", "install", "-q", "-r", "docs/requirements.txt"])
            marca.write_text(atual)


def localizar_bun() -> str:
    for candidato in (shutil.which("bun"), Path.home() / ".bun" / "bin" / ("bun.exe" if WINDOWS else "bun")):
        if candidato and Path(candidato).exists():
            return str(candidato)
    passo("bun não encontrado: instalando pelo instalador oficial (https://bun.sh)")
    if WINDOWS:
        rodar(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "irm bun.sh/install.ps1 | iex"])
    else:
        rodar(["bash", "-c", "curl -fsSL https://bun.sh/install | bash"])
    bun = Path.home() / ".bun" / "bin" / ("bun.exe" if WINDOWS else "bun")
    if not bun.exists():
        sys.exit("Não foi possível instalar o bun. Instale manualmente: https://bun.sh")
    return str(bun)


def preparar_web(bun: str):
    marca, atual = WEB / "node_modules" / ".sma-deps", _hash("web/package.json", "web/bun.lock")
    if not marca.exists() or marca.read_text() != atual:
        passo("Instalando as dependências do dashboard (bun install)")
        rodar([bun, "install"], cwd=WEB)
        marca.write_text(atual)
    else:
        passo("Dependências do dashboard já instaladas")
    indice = WEB / "dist" / "index.html"
    fontes = max(_mais_novo(WEB / "src", {".ts", ".tsx", ".css"}), _mais_novo(WEB / "public", {".svg", ".json"}),
                 (WEB / "index.html").stat().st_mtime)
    if not indice.exists() or indice.stat().st_mtime < fontes:
        passo("Gerando o build do dashboard (bun run build)")
        rodar([bun, "run", "build"], cwd=WEB)
    else:
        passo("Build do dashboard atualizado")


def preparar_traces():
    if not (WEB / "public" / "traces" / "index.json").exists():
        passo("Exportando os traces do replay offline e a comparação com o baseline")
        rodar([PY_VENV, "-m", "fin_mas", "comparar", "--seeds", "10", "--out", "docs/dsm3/resultados"])
        rodar([PY_VENV, "-m", "fin_mas", "export", "--out", "web/public/traces"])


def preparar(bun_necessario=True, docs=False):
    verificar_python()
    preparar_python(docs)
    preparar_traces()
    bun = localizar_bun() if bun_necessario else None
    if bun:
        preparar_web(bun)
    return bun


# ---------------------------------------------------------------- modos
def _abrir_quando_pronto(url, abrir, tentativas=60):
    for _ in range(tentativas):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except OSError:
            time.sleep(0.5)
    print(f"\n   Escritório da SMA em {url}  (Ctrl+C encerra)\n", flush=True)
    if abrir:
        webbrowser.open(url)


def _manter(processos):
    try:
        while all(p.poll() is None for p in processos):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in processos:
            if p.poll() is None:
                p.terminate()


def modo_ao_vivo(args, _bun):
    passo("Iniciando o escritório ao vivo (servidor local, sem internet)")
    # --demo: contas de demonstração com senha pública (o servidor a imprime), para avaliar sem configurar nada.
    # Uso real: `python -m fin_mas instalar` e depois `python -m fin_mas serve --instalacao dados`.
    srv = subprocess.Popen([str(PY_VENV), "-m", "fin_mas", "serve", "--porta", str(args.porta), "--demo",
                            "--scenario", args.cenario or "expediente_sma"], cwd=RAIZ, env=_env())
    _abrir_quando_pronto(f"http://127.0.0.1:{args.porta}", not args.sem_navegador)
    _manter([srv])


def modo_replay(args, bun):
    passo("Iniciando o replay offline (sem servidor Python; traces exportados)")
    web = subprocess.Popen([bun, "run", "preview", "--host", "127.0.0.1", "--port", str(args.porta), "--strictPort"],
                           cwd=WEB, env=_env())
    _abrir_quando_pronto(f"http://127.0.0.1:{args.porta}", not args.sem_navegador)
    _manter([web])


def modo_dev(args, bun):
    passo("Modo desenvolvimento: servidor Python (8765) + Vite com recarga automática (5173)")
    srv = subprocess.Popen([str(PY_VENV), "-m", "fin_mas", "serve", "--porta", "8765", "--demo"], cwd=RAIZ, env=_env())
    web = subprocess.Popen([bun, "run", "dev", "--host", "127.0.0.1"], cwd=WEB, env=_env())
    _abrir_quando_pronto("http://127.0.0.1:5173", not args.sem_navegador)
    _manter([srv, web])


def modo_testes(_args, bun):
    passo("Testes e2e e de integração (pytest, offline)")
    rodar([PY_VENV, "-m", "pytest"])
    passo("Rastreabilidade (tools/trace.py --check)")
    rodar([PY_VENV, "tools/trace.py", "--check"])
    passo("Testes do dashboard (reducer sobre traces reais)")
    rodar([bun, "run", "test"], cwd=WEB)
    passo("Testes de uso real no navegador (Chrome instalado + servidor Python)")
    rodar([bun, "run", "test:e2e"], cwd=WEB)
    print("\n   Todos os testes passaram.", flush=True)


def modo_docs(_args, _bun):
    passo("Gerando a documentação (Sphinx) em docs/_build/html")
    rodar([PY_VENV, "-m", "sphinx", "-b", "html", "docs", "docs/_build/html"])
    print(f"\n   Abra {RAIZ / 'docs' / '_build' / 'html' / 'index.html'}", flush=True)


def modo_cli(args, _bun):
    cmd = [PY_VENV, "-m", "fin_mas", "run", "--scenario", args.cenario or "desvio_irregular"]
    if args.porte:
        cmd += ["--porte", args.porte]
    rodar(cmd)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Prepara o ambiente e executa o SMA de controladoria.")
    parser.add_argument("modo", nargs="?", default="ao-vivo", choices=MODOS)
    parser.add_argument("--porta", type=int, default=None, help="porta do navegador (8765 ao vivo, 4173 replay)")
    parser.add_argument("--cenario", default=None, help="cenário (ao-vivo e cli)")
    parser.add_argument("--porte", default=None, choices=("micro", "pequena", "media", "grande"), help="modo cli")
    parser.add_argument("--sem-navegador", action="store_true", help="não abre o navegador")
    args = parser.parse_args(argv)
    args.porta = args.porta or (4173 if args.modo == "replay" else 8765)
    bun = preparar(bun_necessario=args.modo not in ("docs", "cli"), docs=args.modo == "docs")
    if args.modo == "instalar":
        print("\n   Ambiente pronto. Rode de novo com um modo: ao-vivo, replay, dev, testes, docs ou cli.")
        return 0
    {"ao-vivo": modo_ao_vivo, "replay": modo_replay, "dev": modo_dev, "testes": modo_testes, "docs": modo_docs,
     "cli": modo_cli}[args.modo](args, bun)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as erro:
        sys.exit(f"\nFalhou: {' '.join(map(str, erro.cmd))} (código {erro.returncode})")
