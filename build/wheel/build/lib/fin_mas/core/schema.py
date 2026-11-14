"""Validação de esquema das mensagens A2A (DSM3).

O envelope (remetente, destinatário, performativo, conversa, ontologia, prazo) e o
conteúdo de cada performativo são validados antes de a mensagem mudar o estado de uma
conversa. Os esquemas vêm de `models/protocols.yaml` (`esquemas`): `{campo: tipo}`, com
`?` no fim do tipo para campo opcional. Campos extras são aceitos (extensão compatível);
campo obrigatório ausente ou de tipo errado rejeita a mensagem, sem exceção do Python
escapando para a simulação (era o `KeyError` apontado no feedback da DSM2).
"""
import re

from fin_mas.core.message import ONTOLOGIA, Message

TIPOS = {"str": str, "int": int, "list": list, "dict": dict, "bool": bool, "aaaa-mm": str}
FORMATOS = {"aaaa-mm": (re.compile(r"20\d{2}-(0[1-9]|1[0-2])"),
                        "competência no formato AAAA-MM (ano 2000 a 2099, mês 01 a 12)")}
TAMANHO_MAX_ID = 64


def erros_envelope(msg: Message, agora: int) -> list[str]:
    erros = []
    for campo in ("sender", "receiver", "performative", "conversation_id"):
        valor = getattr(msg, campo, None)
        if not isinstance(valor, str) or not valor.strip():
            erros.append(f"{campo} ausente ou vazio")
        elif len(valor) > TAMANHO_MAX_ID:
            erros.append(f"{campo} com mais de {TAMANHO_MAX_ID} caracteres")
    if msg.protocol is not None and not isinstance(msg.protocol, str):
        erros.append("protocol deve ser texto")
    if not isinstance(msg.content, dict):
        erros.append("content deve ser um objeto (dict)")
    if msg.ontology != ONTOLOGIA:
        erros.append(f"ontologia {msg.ontology!r} diferente de {ONTOLOGIA!r}")
    if msg.reply_by is not None:
        if not _tipo_ok(msg.reply_by, int):
            erros.append("reply_by deve ser inteiro (tempo lógico)")
        elif msg.reply_by <= agora:
            erros.append(f"reply_by={msg.reply_by} não está no futuro (agora={agora})")
    return erros


def erros_conteudo(esquema: dict | None, content: dict) -> list[str]:
    """Campos obrigatórios ausentes e tipos errados do conteúdo."""
    if not esquema:
        return []
    erros = []
    for campo, tipo in esquema.items():
        opcional = tipo.endswith("?")
        esperado = TIPOS[tipo.rstrip("?")]
        if campo not in content or content[campo] is None:
            if not opcional:
                erros.append(f"campo obrigatório ausente: {campo}")
            continue
        if not _tipo_ok(content[campo], esperado):
            erros.append(f"campo {campo} deveria ser {tipo.rstrip('?')}, veio {type(content[campo]).__name__}")
        elif esperado is str and not content[campo].strip():
            erros.append(f"campo {campo} vazio")
        elif tipo.rstrip("?") in FORMATOS:
            padrao, descricao = FORMATOS[tipo.rstrip("?")]
            if not padrao.fullmatch(content[campo]):
                erros.append(f"campo {campo}={content[campo]!r} inválido: {descricao}")
    return erros


def _tipo_ok(valor, esperado) -> bool:
    if esperado is int:
        return isinstance(valor, int) and not isinstance(valor, bool)
    return isinstance(valor, esperado)
