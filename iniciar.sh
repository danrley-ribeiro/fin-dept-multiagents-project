#!/usr/bin/env bash
# Um comando (Linux/macOS): garante o Python 3.11+ e delega tudo a tools/iniciar.py.
#   ./iniciar.sh                  escritório ao vivo
#   ./iniciar.sh replay | dev | testes | docs | cli | instalar
set -euo pipefail
cd "$(dirname "$0")"

for candidato in python3.13 python3.12 python3.11 python3 python; do
  if command -v "$candidato" >/dev/null 2>&1 &&
     "$candidato" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    exec "$candidato" tools/iniciar.py "$@"
  fi
done

echo "Python 3.11+ não encontrado. Instale e rode de novo:" >&2
echo "  Ubuntu/Debian: sudo apt install python3.12 python3.12-venv" >&2
echo "  macOS (Homebrew): brew install python@3.12" >&2
exit 1
