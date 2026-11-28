"""O roteiro do vídeo aponta arquivo, função e linha do código (o professor pediu o vídeo focado no código-fonte).

Cada correção simulada achou referências desatualizadas: uma mudança no código deslocava a função e o roteiro ficava
apontando para outra linha. Este teste lê o roteiro e confere que cada função citada como `arquivo`, `função` (l. N)
está mesmo na linha N. Roda no repositório e dentro do ZIP extraído (o roteiro fica em `apresentacao/`).
"""
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]
ARQUIVO = re.compile(r"`((?:src|tools)/[\w/]+\.py)`")
FUNCAO = re.compile(r"`(?:\w+\.)?(\w+)` \(l\. (\d+)\)")


def _roteiro() -> Path:
    for candidato in (RAIZ / "entregas" / "dsm4" / "apresentacao" / "roteiro.md",
                      RAIZ.parent / "apresentacao" / "roteiro.md"):
        if candidato.is_file():
            return candidato
    pytest.skip("roteiro do vídeo não encontrado")


def test_every_function_line_cited_in_the_video_script_is_current():
    referencias, erradas = 0, []
    for linha_do_roteiro in _roteiro().read_text(encoding="utf-8").splitlines():
        atual = None
        # percorre a linha na ordem: cada `arquivo.py` vale para as funções citadas depois dele
        for m in re.finditer(f"{ARQUIVO.pattern}|{FUNCAO.pattern}", linha_do_roteiro):
            if m.group(1):
                atual = m.group(1)
                continue
            funcao, numero = m.group(2), int(m.group(3))
            if atual is None:
                continue
            referencias += 1
            codigo = (RAIZ / atual).read_text(encoding="utf-8").splitlines()
            alvo = codigo[numero - 1] if numero <= len(codigo) else ""
            if not re.search(rf"\bdef {re.escape(funcao)}\b", alvo):
                achada = next((i for i, x in enumerate(codigo, 1) if re.search(rf"\bdef {re.escape(funcao)}\b", x)), None)
                erradas.append(f"{atual}: {funcao} citada na l. {numero}, está na l. {achada}")
    assert referencias >= 10, f"só {referencias} referências reconhecidas no roteiro"
    assert not erradas, "referências desatualizadas no roteiro:\n" + "\n".join(erradas)
