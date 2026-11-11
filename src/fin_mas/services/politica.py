"""SVC-POL — Política de aprovação e Approval Gate (PROT-APR), DSM3.

Uma decisão humana sobre um veto do AG-CIN deixa de ser uma mensagem livre e passa a
ser um **ticket** emitido pela política e decidido numa conversa PROT-APR. O ticket fica
vinculado a:

- a solicitação (`SOL-…`) e a conversa de conformidade vetada (`CMP-…`) com o seu ciclo;
- o veto: hash SHA-256 dos achados que o humano viu (`veto`);
- a identidade do aprovador designado e às decisões que o papel dele permite;
- um prazo (`expira_em`, no relógio lógico) e às opções que a política deixou abertas.

Política explícita (cada regra tem id e aparece na auditoria):

- POL-01  toda liberação de veto exige aprovação humana (REQUIRE_APPROVAL);
- POL-02  o aprovador decide só o que o seu cadastro permite (ex.: analista não dá waiver);
- POL-03  quem criou ou aprovou um lançamento vetado não decide sobre ele (SoD da aprovação);
- POL-04  waiver exige justificativa com pelo menos `MIN_JUSTIFICATIVA` caracteres e duas palavras
          de três ou mais letras (não aceita "aaaaaaaaaa" nem "ok ok ok");
- POL-05  correção aprovada só pode conter correções sugeridas pelo AG-CIN no veto;
- POL-06  achado crítico reincidente após waiver anterior (memória) não admite novo waiver;
- POL-07  sem opção de liberação restante, a ação é negada (DENY) e a publicação fica bloqueada;
- POL-08  cada aprovação é de uso único: vale para um veto, uma vez, dentro do prazo.

O barramento chama os validadores desta classe antes de mudar o estado de PROT-APR e de
PROT-CMP; o gateway MCP chama `autorizar_efeito` antes de executar a correção no ERP.
"""
import hashlib
import json
import re

from fin_mas.core.fsm import ProtocolViolation

PRAZO_APROVACAO = 20  # ticks lógicos para o aprovador decidir (execução em lote)
MIN_JUSTIFICATIVA = 10
DECISOES = ("waiver", "corrigir", "bloquear")

APROVADORES_PADRAO = {
    "APR": {"pessoa": "controller", "titulo": "Controller", "decisoes": list(DECISOES)},
}


class AprovacaoNecessaria(PermissionError):
    """Efeito externo sem aprovação válida (ApprovalRequired, TEST-12)."""


def _justificativa_valida(texto: str) -> bool:
    palavras = {p.lower() for p in re.findall(r"[^\W\d_]{3,}", texto)}
    return len(texto.strip()) >= MIN_JUSTIFICATIVA and len(palavras) >= 2


def _par(correcao: dict) -> dict:
    return {"lancamento": correcao.get("lancamento"), "acao": correcao.get("acao")}


def digest_veto(achados: list) -> str:
    canonico = json.dumps(achados, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


class PoliticaAprovacao:
    ID = "SVC-POL"

    def __init__(self, bus, aprovadores: dict | None = None, prazo: int = PRAZO_APROVACAO):
        self.bus = bus
        self.aprovadores = {k: dict(v) for k, v in (aprovadores or APROVADORES_PADRAO).items()}
        self.prazo = prazo
        self.tickets: dict[str, dict] = {}  # id da conversa PROT-APR -> ticket
        self.__credencial = bus.register_service(self.ID, "SVC-POL")
        bus.add_validator("PROT-APR", self._validar_apr)
        bus.add_validator("PROT-CMP", self._validar_cmp)

    # ---- emissão e classificação --------------------------------------------------
    def emitir(self, *, solicitacao: str, competencia: str, cmp: str, ciclo: int, veto: dict,
               aprovador: str = "APR") -> dict:
        """Cria o ticket do veto e decide as opções abertas ao humano (POL-01, 06 e 07)."""
        achados = veto["achados"]
        opcoes, negadas = [], []
        reincidentes = [a for a in achados if a["severidade"] == "critica" and a.get("reincidencia")]
        for opcao in veto.get("opcoes", ["waiver", "bloquear"]):
            if opcao == "waiver" and reincidentes:
                negadas.append({"opcao": "waiver", "regra": "POL-06",
                                "motivo": "reincidência após waiver anterior: " + ", ".join(
                                    f"{a['lancamento']} ({a['reincidencia']['memoria']})" for a in reincidentes)})
                continue
            opcoes.append(opcao)
        liberacao = [o for o in opcoes if o in ("waiver", "corrigir")]
        classe = "require_approval" if liberacao else "deny"
        tid = self.bus.new_conversation_id("APR")
        ticket = {
            "id": tid, "solicitacao": solicitacao, "competencia": competencia, "cmp": cmp, "ciclo": ciclo,
            "veto": digest_veto(achados), "achados": achados, "opcoes": opcoes, "negadas": negadas,
            "correcoes_sugeridas": [dict(c) for c in veto.get("correcoes_sugeridas", [])],
            "envolvidos": sorted(veto.get("envolvidos", [])), "aprovador": aprovador, "classe": classe,
            "emitido_em": self.bus.now, "expira_em": self.bus.now + self.prazo, "estado": "emitido",
            "decisao": None, "aprovado_por": None, "justificativa": None, "correcoes_aprovadas": [],
            "executadas": [], "consumido": False,
        }
        self.tickets[tid] = ticket
        self._auditar(tid, "emitido", classe=classe, opcoes=opcoes, negadas=negadas, veto=ticket["veto"],
                      aprovador=aprovador, expira_em=ticket["expira_em"],
                      regra="POL-01" if classe == "require_approval" else "POL-07")
        return ticket

    def conteudo_proposta(self, tid: str) -> dict:
        t = self.tickets[tid]
        return {"solicitacao": t["solicitacao"], "competencia": t["competencia"], "acao": "liberar_publicacao_vetada",
                "cmp": t["cmp"], "veto": t["veto"], "achados": t["achados"], "opcoes": t["opcoes"],
                "negadas": t["negadas"], "correcoes_sugeridas": t["correcoes_sugeridas"], "prazo": t["expira_em"]}

    def classificar(self, tid: str) -> str:
        """Aplica no PROT-APR a classificação do ticket (evento local do SVC-POL)."""
        t = self.tickets[tid]
        self.bus.advance(tid, t["classe"], self.ID, credencial=self.__credencial)
        t["estado"] = "pendente" if t["classe"] == "require_approval" else "negado"
        return t["classe"]

    # ---- validação no barramento ----------------------------------------------------------
    def _validar_apr(self, msg, conv) -> str | None:
        t = self.tickets.get(msg.conversation_id)
        if t is None:
            return f"POL-08: {msg.conversation_id} não é um ticket emitido pela política"
        c = msg.content
        if msg.performative == "propose-action":
            if c.get("veto") != t["veto"] or c.get("opcoes") != t["opcoes"] or c.get("solicitacao") != t["solicitacao"]:
                return "POL-01: proposta diferente do ticket emitido (veto, opções ou solicitação)"
            if msg.receiver != t["aprovador"]:
                return f"POL-02: proposta endereçada a {msg.receiver}, aprovador designado é {t['aprovador']}"
            return None
        # approve / reject: vínculo com o ticket, com o veto e com a identidade do aprovador
        if c.get("aprovacao") != t["id"]:
            return f"POL-08: aprovação {c.get('aprovacao')!r} não corresponde ao ticket {t['id']}"
        if c.get("solicitacao") != t["solicitacao"]:
            return f"POL-08: ticket {t['id']} é da solicitação {t['solicitacao']}, não de {c.get('solicitacao')}"
        if c.get("veto") != t["veto"]:
            return "POL-08: hash do veto não confere: a decisão não se refere aos achados apresentados"
        if t["estado"] != "pendente":
            return f"POL-08: ticket {t['id']} já está {t['estado']} (decisão duplicada ou reutilizada)"
        if self.bus.now + 1 >= t["expira_em"]:  # a entrega (now+1) precisa ocorrer antes do prazo
            return f"POL-08: ticket {t['id']} expira em t={t['expira_em']}; a decisão não seria entregue no prazo"
        cadastro = self.aprovadores.get(msg.sender)
        if msg.sender != t["aprovador"] or cadastro is None:
            return f"POL-02: {msg.sender} não é o aprovador designado ({t['aprovador']})"
        decisao = "bloquear" if msg.performative == "reject" else c.get("decisao")
        if decisao not in cadastro["decisoes"]:
            return f"POL-02: {msg.sender} ({cadastro['titulo']}) não pode decidir '{decisao}'"
        if cadastro["pessoa"] in t["envolvidos"]:
            return f"POL-03: {cadastro['pessoa']} participou de um lançamento vetado e não pode decidir sobre ele"
        if msg.performative == "approve":
            if decisao not in t["opcoes"] or decisao == "bloquear":
                return f"POL-07: decisão '{decisao}' não está entre as opções abertas {t['opcoes']}"
            if decisao == "waiver" and not _justificativa_valida(c["justificativa"]):
                return (f"POL-04: waiver exige justificativa com pelo menos {MIN_JUSTIFICATIVA} caracteres "
                        f"e duas palavras diferentes de três ou mais letras")
            if decisao == "corrigir":
                pedidas = [_par(x) for x in c.get("correcoes") or [] if isinstance(x, dict)]
                if not pedidas:
                    return "POL-05: correção aprovada sem nenhuma correção"
                sugeridas = [_par(x) for x in t["correcoes_sugeridas"]]
                fora = [p for p in pedidas if p not in sugeridas]
                if fora:
                    return f"POL-05: correções fora das sugeridas pelo AG-CIN: {fora}"
                t["correcoes_aprovadas"] = pedidas
        t.update(estado="aprovado" if msg.performative == "approve" else "rejeitado", decisao=decisao,
                 aprovado_por={"agente": msg.sender, "pessoa": cadastro["pessoa"], "titulo": cadastro["titulo"]},
                 justificativa=c["justificativa"], decidido_em=self.bus.now)
        self._auditar(t["id"], "decidido", decisao=decisao, aprovado_por=t["aprovado_por"],
                      correcoes=t["correcoes_aprovadas"], regra="POL-02..05")
        return None

    def _validar_cmp(self, msg, conv) -> str | None:
        if msg.performative not in ("waiver_humano", "correcao"):
            return None
        t = self.tickets.get(msg.content.get("aprovacao"))
        if t is None:
            return f"POL-08: {msg.performative} sem aprovação emitida pela política"
        if t["cmp"] != msg.conversation_id:
            return f"POL-08: aprovação {t['id']} é do veto em {t['cmp']}, não de {msg.conversation_id}"
        if t["consumido"]:
            return f"POL-08: aprovação {t['id']} já foi usada"
        esperado = {"waiver_humano": ("waiver", "aprovado"), "correcao": ("corrigir", "executado")}[msg.performative]
        if (t["decisao"], t["estado"]) != esperado:
            return f"POL-08: aprovação {t['id']} está {t['estado']} com decisão {t['decisao']}, não {esperado}"
        if msg.performative == "correcao":
            enviadas = [{"lancamento": x.get("lancamento"), "acao": x.get("acao")} for x in msg.content["correcoes"]]
            if enviadas != [{"lancamento": x["lancamento"], "acao": x["acao"]} for x in t["executadas"]]:
                return "POL-05: correções informadas ao AG-CIN diferem das executadas com a aprovação"
        t["consumido"] = True
        self._auditar(t["id"], "consumido", cmp=msg.conversation_id, performativo=msg.performative, regra="POL-08")
        return None

    # ---- efeito externo (gateway MCP) ---------------------------------------------------
    def autorizar_efeito(self, aprovacao: str | None, agente: str, lancamento: str, acao: str) -> dict:
        """Confere, antes da execução, que a correção tem aprovação válida (fail-closed)."""
        t = self.tickets.get(aprovacao) if aprovacao else None
        pedido = {"lancamento": lancamento, "acao": acao}
        if t is None:
            raise AprovacaoNecessaria(f"{acao} em {lancamento}: sem aprovação (PROT-APR)")
        if t["estado"] != "aprovado" or t["decisao"] != "corrigir":
            raise AprovacaoNecessaria(f"{acao} em {lancamento}: aprovação {t['id']} está {t['estado']}")
        if pedido not in t["correcoes_aprovadas"]:
            raise AprovacaoNecessaria(f"{acao} em {lancamento}: fora das correções aprovadas em {t['id']}")
        if any(x["lancamento"] == lancamento and x["acao"] == acao for x in t["executadas"]):
            raise AprovacaoNecessaria(f"{acao} em {lancamento}: já executada com {t['id']} (uso único)")
        return t

    def registrar_execucao(self, aprovacao: str, registro: dict) -> None:
        t = self.tickets[aprovacao]
        t["executadas"].append(registro)
        self._auditar(aprovacao, "efeito_executado", registro=registro, regra="POL-05")
        self._fechar_execucao(t)

    def registrar_falha(self, aprovacao: str, pedido: dict, motivo: str) -> None:
        t = self.tickets[aprovacao]
        t.setdefault("falhas", []).append({**pedido, "motivo": motivo})
        self._auditar(aprovacao, "efeito_falhou", pedido=pedido, motivo=motivo, regra="POL-05")
        self._fechar_execucao(t)

    @staticmethod
    def _fechar_execucao(t) -> None:
        if len(t["executadas"]) + len(t.get("falhas", [])) == len(t["correcoes_aprovadas"]):
            t["estado"] = "executado"

    def expirar(self, tid: str) -> None:
        """Prazo esgotado sem decisão, ou aprovado sem execução: o ticket não vale mais (fail-closed)."""
        t = self.tickets.get(tid)
        if t and not t["consumido"] and t["estado"] in ("pendente", "aprovado"):
            anterior, t["estado"] = t["estado"], "expirado"
            self._auditar(tid, "expirado", anterior=anterior, regra="POL-08")

    def ticket(self, tid: str) -> dict:
        if tid not in self.tickets:
            raise ProtocolViolation(f"ticket inexistente: {tid}")
        return self.tickets[tid]

    def _auditar(self, tid, evento, **campos) -> None:
        self.bus.audit.record(self.bus.now, "politica", conversation_id=tid, agente=self.ID, evento=evento, **campos)
