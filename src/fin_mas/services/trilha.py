"""Trilha de acesso do SVC-IAM: quem entrou, quem tentou, quem mudou o quê (NORM-13, ADR-009).

Um arquivo JSONL só de acréscimo. Cada registro carrega o hash do anterior (cadeia, a mesma
regra do trace: `services/audit._elo`), e a **cabeça** da cadeia (quantidade de registros,
hash final e HMAC) fica fora da pasta de dados, junto das chaves. `verificar()` refaz a
cadeia e confere a cabeça: alterar, remover ou truncar registros é detectado.

Os registros passam pela redação de segredos (`services/redacao.py`): senha e token nunca
entram aqui. Sem `caminho`, a trilha fica em memória (acesso simulado).
"""
import hashlib
import hmac
import json
from pathlib import Path

from fin_mas.services.audit import _elo
from fin_mas.services.redacao import redigir
from fin_mas.services.selado import _estado, chave_de, trava

GENESE = "0" * 64


class TrilhaAdulterada(RuntimeError):
    pass


class TrilhaAcesso:
    def __init__(self, caminho=None):
        self.caminho = Path(caminho) if caminho else None
        self._memoria: list[dict] = []
        self._chave = chave_de("trilha", self.caminho) if self.caminho else b""

    def registrar(self, t: float, evento: str, *, ator: str | None, resultado: str = "ok", **campos) -> dict:
        registro = redigir({"t": round(float(t), 3), "evento": evento, "ator": ator, "resultado": resultado, **campos})
        if self.caminho is None:
            registro["seq"] = len(self._memoria) + 1
            self._memoria.append(registro)
            return registro
        with trava(self.caminho):
            cabeca = self._cabeca()
            registro["seq"] = cabeca["registros"] + 1
            registro["_hash"] = _elo(cabeca["hash_final"], registro)
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            with open(self.caminho, "a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False, sort_keys=True) + "\n")
            self._gravar_cabeca(registro["seq"], registro["_hash"])
        return registro

    # ---- cabeça da cadeia (fora da pasta de dados) ------------------------------------
    def _arquivo_cabeca(self) -> Path:
        return _estado("trilha", self.caminho, "cabeca")

    def _hmac(self, registros: int, hash_final: str) -> str:
        return hmac.new(self._chave, f"{registros}|{hash_final}".encode("utf-8"), hashlib.sha256).hexdigest()

    def _cabeca(self) -> dict:
        try:
            c = json.loads(self._arquivo_cabeca().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"registros": 0, "hash_final": GENESE}
        if not hmac.compare_digest(str(c.get("hmac")), self._hmac(c.get("registros"), c.get("hash_final"))):
            raise TrilhaAdulterada("cabeça da trilha de acesso com selo inválido")
        return c

    def _gravar_cabeca(self, registros: int, hash_final: str) -> None:
        arquivo = self._arquivo_cabeca()
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(json.dumps({"registros": registros, "hash_final": hash_final,
                                       "hmac": self._hmac(registros, hash_final)}), encoding="utf-8")

    # ---- leitura e verificação -----------------------------------------------------------
    def ler(self) -> list[dict]:
        if self.caminho is None:
            return [dict(r) for r in self._memoria]
        if not self.caminho.exists():
            return []
        return [json.loads(linha) for linha in self.caminho.read_text(encoding="utf-8").splitlines() if linha.strip()]

    def verificar(self) -> dict:
        """Refaz a cadeia e confere a cabeça. Levanta `TrilhaAdulterada`; devolve o resumo se íntegra."""
        if self.caminho is None:
            return {"registros": len(self._memoria), "hash_final": None}
        cabeca = self._cabeca()
        try:
            registros = self.ler()
        except ValueError:
            raise TrilhaAdulterada("trilha de acesso com linha ilegível") from None
        anterior = GENESE
        for n, r in enumerate(registros, start=1):
            corpo = {k: v for k, v in r.items() if k != "_hash"}
            if r.get("seq") != n or r.get("_hash") != _elo(anterior, corpo):
                raise TrilhaAdulterada(f"cadeia quebrada no registro {n} da trilha de acesso (alterado ou removido)")
            anterior = r["_hash"]
        if len(registros) != cabeca["registros"] or anterior != cabeca["hash_final"]:
            raise TrilhaAdulterada(f"trilha de acesso truncada ou estendida fora do sistema: {len(registros)} "
                                   f"registro(s), a cabeça selada aponta {cabeca['registros']}")
        return {"registros": len(registros), "hash_final": anterior}
