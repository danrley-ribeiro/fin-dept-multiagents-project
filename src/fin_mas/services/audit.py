"""Auditoria: registro central de eventos (SVC-AUD), em memória.

Cada registro é um dict com t (relógio lógico) e seq; o bus e os agentes gravam
por aqui, nunca cada agente por conta própria (REQ-O01).

DSM3 (proteção de informações):
- todo registro passa por redaction antes de ser guardado (NORM-06); se a sanitização
  falhar, o conteúdo é recusado e fica só um marcador `redacao: recusada` (fail-closed);
- o JSONL gravado tem hash encadeado (`_hash` = SHA-256 do hash anterior + registro) e uma
  última linha de **selo** com o número de registros, o hash final e um HMAC-SHA256 desses dois
  valores com a chave local do trace (`FIN_MAS_CHAVE_TRACE` ou `~/.fin_mas/chave_trace`, fora
  do repositório). `read_jsonl` confere cadeia e selo: acusa linha alterada, removida,
  reordenada, corte do fim do arquivo e cadeia recalculada por quem não tem a chave.
"""
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from fin_mas.services.redacao import FalhaRedacao, redigir

GENESIS = "0" * 64


class TraceAdulterado(ValueError):
    """A cadeia de hashes do trace JSONL não confere."""


class AuditLog:
    encadeado = True  # False: lido de um JSONL sem cadeia de hashes (anterior à DSM3)
    hash_final: str | None = None  # último elo da cadeia, depois de verificado (âncora pública)

    def hash_cadeia(self) -> str:
        """Hash final da cadeia dos registros atuais: o valor a publicar como âncora do trace."""
        anterior = GENESIS
        for r in self.records:
            anterior = _elo(anterior, r)
        return anterior

    def __init__(self):
        self.records: list[dict] = []
        self._ouvintes: list = []

    def record(self, t: int, kind: str, **campos) -> dict:
        try:
            campos = redigir(campos)
        except FalhaRedacao as erro:
            campos = {k: campos[k] for k in ("conversation_id", "agente") if isinstance(campos.get(k), str)}
            campos.update(redacao="recusada", motivo=str(erro))
        registro = {"seq": len(self.records) + 1, "t": t, "kind": kind, **campos}
        self.records.append(registro)
        for ouvinte in self._ouvintes:
            ouvinte(registro)
        return registro

    def subscribe(self, ouvinte) -> None:
        """Recebe cada registro novo (transmissão ao vivo para o dashboard)."""
        self._ouvintes.append(ouvinte)

    def by_conversation(self, conversation_id: str) -> list[dict]:
        return [r for r in self.records if r.get("conversation_id") == conversation_id]

    def familia(self, conversation_id: str) -> list[str]:
        """A conversa e as filhas ligadas por registros `link` (subtarefas, consultas), em ordem de abertura."""
        filhas = {}
        for r in self.records:
            if r["kind"] == "link":
                filhas.setdefault(r["conversation_id"], []).append(r["filha"])
        ordem, pendentes = [], [conversation_id]
        while pendentes:
            atual = pendentes.pop(0)
            ordem.append(atual)
            pendentes += filhas.get(atual, [])
        return ordem

    def trilha(self, conversation_id: str, verbose: bool = False) -> list[str]:
        """Sequência causal da solicitação reconstruída só pelo trace (REQ-O01)."""
        familia = set(self.familia(conversation_id))
        ocultos = set() if verbose else {"deliver"}
        return [formatar(r) for r in self.records
                if r.get("conversation_id") in familia and r["kind"] not in ocultos]

    def write_jsonl(self, path, chave: bytes | None = None) -> None:
        """Grava um registro por linha (JSONL), na ordem de seq, com hash encadeado e selo HMAC no fim."""
        linhas, anterior = [], GENESIS
        for r in self.records:
            anterior = _elo(anterior, r)
            linhas.append(json.dumps({**r, "_hash": anterior}, sort_keys=True, ensure_ascii=False))
        selo = {"registros": len(self.records), "hash_final": anterior}
        selo["hmac"] = _hmac_selo(chave or chave_trace(), selo)
        linhas.append(json.dumps({"_selo": selo}, sort_keys=True))
        Path(path).write_text("\n".join(linhas) + "\n", encoding="utf-8")

    @classmethod
    def read_jsonl(cls, path, verificar: bool = True, chave: bytes | None = None,
                   ancora: str | None = None) -> "AuditLog":
        """Lê o trace; com `verificar`, levanta TraceAdulterado se cadeia ou selo não conferirem.

        Com `ancora` (hash final publicado, ex.: no README ou num commit), a verificação dispensa a
        chave local: confere a cadeia, o número de registros e se o hash final é o publicado. Serve
        para quem não tem a chave do autor (o professor, em outra máquina).
        """
        log, anterior, encadeado, selo = cls(), GENESIS, None, None
        linhas = [x for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
        for n, linha in enumerate(linhas, start=1):
            r = json.loads(linha)
            if "_selo" in r:
                if n != len(linhas):
                    raise TraceAdulterado(f"linha {n}: selo fora da última linha; trace alterado")
                selo = r["_selo"]
                continue
            gravado = r.pop("_hash", None)
            if encadeado is None:
                encadeado = gravado is not None  # trace anterior à DSM3 não tem cadeia
                log.encadeado = encadeado
            if verificar and (encadeado or gravado is not None):
                anterior = _elo(anterior, r)
                if gravado != anterior:
                    raise TraceAdulterado(f"linha {n} (seq {r.get('seq')}): hash não confere; trace alterado")
            log.records.append(r)
        if encadeado is None:  # arquivo vazio
            log.encadeado = False
        if verificar and (encadeado or selo is not None):
            if not isinstance(selo, dict):
                raise TraceAdulterado("selo final ausente: trace truncado ou incompleto")
            if ancora is not None:
                if anterior != ancora:
                    raise TraceAdulterado(f"hash final {anterior[:16]}… difere da âncora publicada {ancora[:16]}…")
            else:
                esperado = _hmac_selo(chave or chave_trace(), {"registros": selo.get("registros"),
                                                               "hash_final": selo.get("hash_final")})
                if not hmac.compare_digest(str(selo.get("hmac")), esperado):
                    raise TraceAdulterado("selo HMAC não confere com a chave local: o trace foi alterado ou foi "
                                          "gravado com outra chave (sem a chave do autor, verifique com "
                                          "--ancora <hash final publicado>)")
            log.hash_final = anterior
            if selo.get("registros") != len(log.records) or selo.get("hash_final") != anterior:
                raise TraceAdulterado(f"selo não confere: {len(log.records)} registros lidos, "
                                      f"{selo.get('registros')} gravados (linhas removidas do fim?)")
        return log

    def digest(self) -> str:
        canonico = json.dumps(self.records, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def chave_trace() -> bytes:
    """Chave local do selo dos traces: variável de ambiente ou arquivo no diretório do usuário (0600)."""
    if os.environ.get("FIN_MAS_CHAVE_TRACE"):
        return os.environ["FIN_MAS_CHAVE_TRACE"].encode("utf-8")
    arquivo = Path.home() / ".fin_mas" / "chave_trace"
    if not arquivo.exists():
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_bytes(secrets.token_bytes(32))
        try:
            os.chmod(arquivo, 0o600)
        except OSError:
            pass
    return arquivo.read_bytes()


def _hmac_selo(chave: bytes, selo: dict) -> str:
    return hmac.new(chave, f"{selo['registros']}:{selo['hash_final']}".encode("utf-8"), hashlib.sha256).hexdigest()


def _elo(anterior: str, registro: dict) -> str:
    canonico = json.dumps(registro, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((anterior + canonico).encode("utf-8")).hexdigest()


def formatar(r: dict) -> str:
    """Uma linha legível por registro do trace."""
    cab = f"t={r['t']:03d} #{r['seq']:03d} {r.get('conversation_id') or '-':<8}"
    k = r["kind"]
    if k in ("open", "send", "deliver", "ui"):
        estados = f"  [{r['de']} -> {r['para']}]" if "de" in r else ""
        return f"{cab} {r['sender']} -> {r['receiver']} {r['performative']}{estados}"
    if k == "drop":
        return f"{cab} PERDIDA {r['sender']} -> {r['receiver']} {r['performative']} ({r['motivo']})"
    if k == "discard":
        return f"{cab} DESCARTADA {r['sender']} -> {r['receiver']} {r['performative']} ({r['motivo']})"
    if k == "timeout":
        return f"{cab} TIMEOUT contra {r['content'].get('contraparte')}  [{r['de']} -> {r['para']}]"
    if k == "advance":
        return f"{cab} {r['agente']} aplica '{r['evento']}'  [{r['de']} -> {r['para']}]"
    if k == "decision":
        resultado = json.dumps(r["resultado"], sort_keys=True, ensure_ascii=False)
        return f"{cab} DECISAO {r['agente']}: {r['regra']} => {resultado}"
    if k == "mcp_call":
        return f"{cab} MCP {r['agente']} chama {r['tool']}"
    if k == "mcp_denied":
        if r.get("motivo"):
            return f"{cab} MCP INDISPONIVEL {r['agente']} em {r['tool']} ({r['motivo']})"
        return f"{cab} MCP NEGADO {r['agente']} em {r['tool']}"
    if k == "link":
        return f"{cab} subconversa {r['filha']} ({r['subtarefa']})"
    if k == "belief":
        return f"{cab} CRENCA {r['agente']}: {r['chave']} = {_curto(r['depois'])} (fonte: {r['fonte']})"
    if k == "desire":
        return f"{cab} DESEJO {r['agente']}: {r['desejo']} {r['evento']} (p{r['prioridade']}; {r['motivo']})"
    if k == "deliberation":
        opcoes = "; ".join(f"{o['plano']}{'' if o['aplicavel'] else ' x'} u={o['utilidade']}" for o in r["opcoes"])
        return f"{cab} DELIBERA {r['agente']}: {r['desejo']} -> {r['escolhido']} [{opcoes}]"
    if k == "intention":
        return f"{cab} INTENCAO {r['agente']}: {r['intencao']} {r['plano']} {r['evento']} ({r['motivo']})"
    if k == "agente":
        return f"{cab} OPERADOR {r['agente']} {r['evento']}"
    if k == "rejected":
        quem = r.get("sender") or r.get("agente")
        alvo = f"{quem} -> {r['receiver']} {r.get('performative')}" if r.get("receiver") else \
            f"{quem} aplica '{r.get('evento')}'"
        return f"{cab} REJEITADA [{r.get('etapa')}] {alvo} ({r.get('motivo')})"
    if k == "erro_agente":
        return f"{cab} ERRO {r.get('agente')} ao tratar {r.get('performative', '-')}: {r.get('erro')}"
    if k == "politica":
        extra = {"emitido": lambda: f"{r.get('classe')} opções={r.get('opcoes')} veto={str(r.get('veto'))[:12]}",
                 "decidido": lambda: f"{r.get('decisao')} por {(r.get('aprovado_por') or {}).get('titulo')}",
                 "consumido": lambda: f"usado por {r.get('performativo')} em {r.get('cmp')}"}.get(r.get("evento"),
                                                                                                   lambda: "")()
        return f"{cab} POLITICA {r.get('regra', '')} ticket {r.get('evento')} {extra}".rstrip()
    if k == "ataques":
        bloqueados = sum(1 for x in r["resultados"] if not x["aceito"])
        return f"{cab} ATAQUES {bloqueados} de {len(r['resultados'])} rejeitados (aprovação {r.get('aprovacao')})"
    if k == "ambiente":
        return f"{cab} AMBIENTE {r.get('evento')}"
    if k == "memoria":
        alvo = r.get("memoria") or r.get("memorias") or r.get("chave") or ""
        motivo = f" ({r['motivo']})" if r.get("motivo") else ""
        return f"{cab} MEMORIA {r.get('evento')} {r.get('tipo', '')} {alvo}{motivo}".rstrip()
    if k == "meta":
        return f"{cab} META {r.get('empresa', {}).get('razao_social', '')}"
    return f"{cab} {k}"


def _curto(valor, limite=80) -> str:
    texto = json.dumps(valor, sort_keys=True, ensure_ascii=False)
    return texto if len(texto) <= limite else texto[: limite - 3] + "..."
