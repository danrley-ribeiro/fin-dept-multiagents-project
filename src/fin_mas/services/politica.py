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

Com o SVC-IAM ligado (`acesso`, ADR-009), a decisão deixa de valer pela caixa `APR` e passa a
valer pela **pessoa autenticada** que a tomou:

- POL-09  a decisão leva um atestado de sessão (`services/iam.py`): sem ele, com atestado de
          outra decisão, de sessão expirada ou revogada, repetido ou de quem não é aprovador,
          a decisão é recusada;
- POL-02 e POL-03 passam a conferir a pessoa real: o cargo da conta define o que ela decide,
          e quem criou ou aprovou um lançamento vetado (vínculo da conta com a pessoa do ERP)
          não decide sobre ele;
- POL-13  quem fez a solicitação não decide sobre ela; onde só há uma pessoa (porte com
          controle compensatório registrado), a decisão passa e o controle fica anotado.

Sem `acesso` (cenários em lote da primeira versão da DSM3) valem as regras POL-01 a POL-08
com o cadastro por identidade, como antes.

DSM4 (ADR-012), também só com o SVC-IAM ligado. O AG-CIN informa no veto a `exposicao` (soma, em
centavos, dos lançamentos críticos sob decisão):

- POL-10  alçada por pessoa: quem libera (waiver ou correção) precisa ter, no porte, alçada que
          cubra a exposição (`limites_alcada` de `models/portes.yaml`; o cargo `controller` usa a
          maior alçada do porte). Bloquear não libera valor e não depende de alçada;
- POL-11  delegação: a decisão pode citar uma delegação (`delegacao`) de outro aprovador; vale o
          cargo e a alçada de quem delegou, limitada ao teto, dentro do prazo e do escopo, sem
          subdelegação; envolvimento (POL-03) e solicitação (POL-13) valem para as duas pessoas;
          a decisão registra "por delegação de";
- POL-12  dupla aprovação: acima de `dupla_aprovacao` do porte, a liberação exige duas pessoas
          diferentes: a primeira dá o aval (`endorse`, o ticket continua PENDENTE e conta o aval),
          a segunda aprova a mesma decisão. As regras de cargo, alçada, envolvimento e
          solicitante valem para as duas;
- POL-14  escalonamento: com `escalonamento_percentual` na política do cadastro, o ticket nasce
          no menor nível de cargo cuja alçada cobre a exposição; níveis acima só decidem depois
          que o ticket escala, sem decisão em X% do prazo (um nível, uma vez, registrado).

O barramento chama os validadores desta classe antes de mudar o estado de PROT-APR e de
PROT-CMP; o gateway MCP chama `autorizar_efeito` antes de executar a correção no ERP.
"""
import hashlib
import json
import math
import re

from fin_mas.core import permissoes
from fin_mas.core.fsm import ProtocolViolation

PRAZO_APROVACAO = 20  # ticks lógicos para o aprovador decidir (execução em lote)
MIN_JUSTIFICATIVA = 10
DECISOES = ("waiver", "corrigir", "bloquear")

APROVADORES_PADRAO = {
    "APR": {"pessoa": "controller", "titulo": "Controller", "decisoes": list(DECISOES)},
}


def _reais(centavos) -> str:
    if centavos is None or centavos == float("inf"):
        return "sem limite"
    return "R$ " + f"{int(centavos) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class AprovacaoNecessaria(PermissionError):
    """Efeito externo sem aprovação válida (ApprovalRequired, TEST-12)."""


def _justificativa_valida(texto: str) -> bool:
    palavras = {p.lower() for p in re.findall(r"[^\W\d_]{3,}", texto)}
    return len(texto.strip()) >= MIN_JUSTIFICATIVA and len(palavras) >= 2


def _par(correcao: dict) -> dict:
    return {"lancamento": correcao.get("lancamento"), "acao": correcao.get("acao")}


def digest_decisao(conteudo: dict) -> str:
    """Corpo da decisão que o atestado cobre: justificativa, correções pedidas e, se houver, a delegação usada."""
    corpo = {"justificativa": conteudo.get("justificativa"),
             "correcoes": [_par(x) for x in conteudo.get("correcoes") or [] if isinstance(x, dict)]}
    if conteudo.get("delegacao") is not None:  # só quando citada: decisões sem delegação têm o digest de antes
        corpo["delegacao"] = conteudo.get("delegacao")
    return hashlib.sha256(json.dumps(corpo, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def digest_veto(achados: list) -> str:
    canonico = json.dumps(achados, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


class PoliticaAprovacao:
    ID = "SVC-POL"

    def __init__(self, bus, aprovadores: dict | None = None, prazo: int = PRAZO_APROVACAO, acesso=None,
                 controle_compensatorio: str | None = None, perfil: dict | None = None):
        self.bus = bus
        self.aprovadores = {k: dict(v) for k, v in (aprovadores or APROVADORES_PADRAO).items()}
        self.prazo = prazo
        self.acesso = acesso  # SVC-IAM: com ele, a decisão vale pela pessoa autenticada (POL-09, POL-13)
        self.controle_compensatorio = controle_compensatorio  # texto do porte em que uma pessoa acumula funções
        self.tickets: dict[str, dict] = {}  # id da conversa PROT-APR -> ticket
        self.perfil = perfil or {}  # porte: limites_alcada, aprovadores e dupla_aprovacao (POL-10, 12, 14)
        self.empresa: str | None = None  # empresa desta execução (IAM-09), com várias empresas no cadastro
        self.ao_escalar: list = []  # quem é avisado quando um ticket escala (POL-14)
        self.__credencial = bus.register_service(self.ID, "SVC-POL")
        bus.add_validator("PROT-APR", self._validar_apr)
        bus.add_validator("PROT-CMP", self._validar_cmp)

    # ---- emissão e classificação --------------------------------------------------
    def emitir(self, *, solicitacao: str, competencia: str, cmp: str, ciclo: int, veto: dict,
               aprovador: str = "APR", solicitado_por: str | None = None) -> dict:
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
        if solicitado_por:
            ticket["solicitado_por"] = solicitado_por  # pessoa autenticada que fez o pedido (POL-13)
        extras = self._avancado(ticket, veto) if self.acesso is not None else {}
        self.tickets[tid] = ticket
        self._auditar(tid, "emitido", classe=classe, opcoes=opcoes, negadas=negadas, veto=ticket["veto"],
                      aprovador=aprovador, expira_em=ticket["expira_em"],
                      regra="POL-01" if classe == "require_approval" else "POL-07", **extras)
        if ticket.get("escalona_em") is not None and classe == "require_approval":
            self.bus.agendar(ticket["escalona_em"], lambda: self._escalar(tid), f"escalonamento de {tid} (POL-14)")
        return ticket

    # ---- DSM4: exposição, dupla aprovação e escalonamento ---------------------------------------
    def _niveis(self) -> list[str]:
        """Cargos aprovadores do porte, do menor para o maior em alçada."""
        limites = self.perfil.get("limites_alcada") or {}
        return sorted((c for c in self.perfil.get("aprovadores") or [] if c in limites),
                      key=lambda c: permissoes.alcada(c, limites))

    def _avancado(self, ticket: dict, veto: dict) -> dict:
        exposicao = veto.get("exposicao")
        if not isinstance(exposicao, int) or isinstance(exposicao, bool):
            return {}
        ticket["exposicao"] = exposicao
        limite = self.perfil.get("dupla_aprovacao")
        ticket["dupla"] = limite is not None and exposicao > limite
        ticket["endossos"] = []
        extras = {"exposicao": exposicao, "dupla": ticket["dupla"]}
        pct = (self.acesso.politica() or {}).get("escalonamento_percentual")
        niveis = self._niveis()
        if pct and niveis:
            limites = self.perfil["limites_alcada"]
            ticket["nivel"] = next((c for c in niveis if permissoes.alcada(c, limites) >= exposicao), niveis[-1])
            ticket["escalona_em"] = ticket["emitido_em"] + max(1, math.ceil(self.prazo * pct / 100))
            extras.update(nivel=ticket["nivel"], escalona_em=ticket["escalona_em"])
        return extras

    def _escalar(self, tid: str) -> None:
        t = self.tickets.get(tid)
        niveis = self._niveis()
        if t is None or t["estado"] != "pendente" or t.get("nivel") not in niveis or t["nivel"] == niveis[-1]:
            return
        anterior, t["nivel"] = t["nivel"], niveis[niveis.index(t["nivel"]) + 1]
        t["escalado_em"] = self.bus.now
        self._auditar(tid, "escalado", de=anterior, para=t["nivel"], regra="POL-14")
        self.acesso.registrar("ticket_escalado", None, ticket=tid, de=anterior, para=t["nivel"], regra="POL-14")
        for ouvinte in list(self.ao_escalar):
            ouvinte(tid)

    def conteudo_proposta(self, tid: str) -> dict:
        t = self.tickets[tid]
        return {"solicitacao": t["solicitacao"], "competencia": t["competencia"], "acao": "liberar_publicacao_vetada",
                "cmp": t["cmp"], "veto": t["veto"], "achados": t["achados"], "opcoes": t["opcoes"],
                "negadas": t["negadas"], "correcoes_sugeridas": t["correcoes_sugeridas"], "prazo": t["expira_em"],
                **({"exposicao": t["exposicao"], "dupla": t["dupla"]} if "exposicao" in t else {})}

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
        compensatorio = None
        if msg.performative == "endorse" and not t.get("dupla"):
            return f"POL-12: o ticket {t['id']} não exige dupla aprovação: decida com approve ou reject"
        if self.acesso is not None:  # a decisão vale pela pessoa autenticada, não pela caixa APR
            cadastro, motivo, compensatorio = self._validar_pessoa(t, c, decisao, msg.performative)
            if motivo:
                return motivo
        elif decisao not in cadastro["decisoes"]:
            return f"POL-02: {msg.sender} ({cadastro['titulo']}) não pode decidir '{decisao}'"
        elif cadastro["pessoa"] in t["envolvidos"]:
            return f"POL-03: {cadastro['pessoa']} participou de um lançamento vetado e não pode decidir sobre ele"
        if msg.performative in ("approve", "endorse"):
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
                if msg.performative == "approve":
                    t["correcoes_aprovadas"] = pedidas
        if msg.performative == "endorse":
            aval = {"pessoa": cadastro["pessoa"], "sessao": cadastro["sessao"], "decisao": decisao,
                    "correcoes": [_par(x) for x in c.get("correcoes") or [] if isinstance(x, dict)],
                    **({"por_delegacao_de": cadastro["por_delegacao_de"]} if "por_delegacao_de" in cadastro else {})}
            t["endossos"].append(aval)
            self._auditar(t["id"], "endossado", aval=aval, endossos=len(t["endossos"]), regra="POL-12")
            self.acesso.registrar("aval", cadastro["pessoa"], ticket=t["id"], decisao=decisao, regra="POL-12")
            return None
        aprovado_por = {"agente": msg.sender, "pessoa": cadastro["pessoa"], "titulo": cadastro["titulo"],
                        **({"sessao": cadastro["sessao"]} if "sessao" in cadastro else {})}
        for campo in ("por_delegacao_de", "delegacao", "aval"):
            if campo in cadastro:
                aprovado_por[campo] = cadastro[campo]
        t.update(estado="aprovado" if msg.performative == "approve" else "rejeitado", decisao=decisao,
                 aprovado_por=aprovado_por, justificativa=c["justificativa"], decidido_em=self.bus.now)
        extras = {"controle_compensatorio": compensatorio} if compensatorio else {}
        if "alcada" in cadastro:
            extras.update(exposicao=t.get("exposicao"), alcada=cadastro["alcada"])
        self._auditar(t["id"], "decidido", decisao=decisao, aprovado_por=t["aprovado_por"],
                      correcoes=t["correcoes_aprovadas"],
                      regra="POL-02..05" if self.acesso is None else "POL-02..05, POL-09, POL-13" + (
                          ", POL-10..12" if "alcada" in extras else ""), **extras)
        if self.acesso is not None:
            self.acesso.registrar("decisao", cadastro["pessoa"], ticket=t["id"], decisao=decisao,
                                  solicitacao=t["solicitacao"], **extras)
        return None

    def _validar_pessoa(self, t, c, decisao, performativo="approve") -> tuple[dict | None, str | None, str | None]:
        """(cadastro da pessoa, motivo da recusa, controle compensatório aplicado)."""
        from fin_mas.services.iam import AcessoNegado
        try:
            sessao = self.acesso.verificar_atestado(c.get("atestado"), ticket=t["id"], veto=t["veto"], decisao=decisao,
                                                    corpo=digest_decisao(c))
        except AcessoNegado as erro:
            pessoa = (c.get("atestado") or {}).get("pessoa") if isinstance(c.get("atestado"), dict) else None
            self.acesso.registrar("decisao", pessoa if isinstance(pessoa, str) else None, "negado", regra=erro.regra,
                                  motivo=erro.motivo, ticket=t["id"])
            return None, str(erro), None

        def negar(regra, motivo):
            self.acesso.registrar("decisao", sessao.usuario, "negado", regra=regra, motivo=motivo, ticket=t["id"])
            return None, f"{regra}: {motivo}", None

        if self.empresa is not None and self.acesso.multiempresa() and sessao.empresa != self.empresa:
            return negar("IAM-09", f"{sessao.usuario} está na empresa {sessao.empresa}; este ticket é da empresa "
                                   f"{self.empresa}")
        delegante, delegacao = None, None
        if c.get("delegacao") is not None:  # POL-11: decide com o cargo e a alçada de quem delegou
            try:
                achada = self.acesso.delegacao_para_decisao(c.get("delegacao"), sessao.usuario, t)
            except AcessoNegado as erro:
                return negar(erro.regra, erro.motivo)
            delegante, delegacao = achada["conta"], achada["delegacao"]
        cargo_efetivo = delegante["cargo"] if delegante else sessao.cargo
        cargo = cargo_efetivo or "sem cargo"
        quem = f"{sessao.usuario} (por delegação de {delegante['usuario']})" if delegante else sessao.usuario
        if decisao not in permissoes.decisoes_do_cargo(cargo_efetivo):
            return negar("POL-02", f"{quem} ({cargo}) não pode decidir '{decisao}'")
        pessoas = [(sessao.pessoa_erp, sessao.usuario)] + ([(delegante.get("pessoa_erp"), delegante["usuario"])]
                                                           if delegante else [])
        for pessoa_erp, nome in pessoas:
            if pessoa_erp and pessoa_erp in t["envolvidos"]:
                return negar("POL-03", f"{nome} participou de um lançamento vetado e não pode decidir sobre ele")
        compensatorio = None
        for _, nome in pessoas:
            if t.get("solicitado_por") and t["solicitado_por"] == nome:
                if not self.controle_compensatorio:
                    return negar("POL-13", f"{nome} fez a solicitação {t['solicitacao']} e não pode decidir sobre ela")
                compensatorio = self.controle_compensatorio
        cadastro = {"pessoa": sessao.usuario, "titulo": cargo, "sessao": sessao.id}
        if delegante:
            cadastro.update(por_delegacao_de=delegante["usuario"], delegacao=delegacao["id"])
        if t.get("exposicao") is None:
            return cadastro, None, compensatorio
        motivo = self._alcada_e_dupla(t, cadastro, cargo_efetivo, delegacao, decisao, performativo, c, quem)
        if motivo:
            return negar(*motivo)
        return cadastro, None, compensatorio

    def _alcada_e_dupla(self, t, cadastro, cargo, delegacao, decisao, performativo, c, quem):
        """POL-14, POL-10 e POL-12 (só com a exposição informada); devolve (regra, motivo) ou None."""
        limites = self.perfil.get("limites_alcada") or {}
        niveis = self._niveis()
        if t.get("nivel") in niveis:
            posicao = niveis.index(cargo) if cargo in niveis else len(niveis) - 1
            if posicao > niveis.index(t["nivel"]):
                return ("POL-14", f"o ticket {t['id']} está no nível {t['nivel']}: {quem} ({cargo}) só decide se ele "
                                  f"escalar (sem decisão até t={t['escalona_em']})")
        if decisao == "bloquear":
            return None  # bloquear não libera valor: não depende de alçada nem de duas pessoas
        alcada = permissoes.alcada(cargo, limites)
        if delegacao is not None and alcada is not None:
            alcada = min(alcada, float(delegacao["teto"]))
        if alcada is None or t["exposicao"] > alcada:
            texto = "sem alçada no porte" if alcada is None else f"alçada de {_reais(alcada)}"
            return ("POL-10", f"{quem} ({cargo or 'sem cargo'}, {texto}) não libera {_reais(t['exposicao'])} "
                              f"em exposição")
        cadastro["alcada"] = None if alcada == float("inf") else int(alcada)
        if not t.get("dupla"):
            return None
        if performativo == "endorse":
            if t["endossos"]:
                return ("POL-12", f"o ticket {t['id']} já tem o aval de {t['endossos'][0]['pessoa']}: falta a "
                                  f"aprovação de outra pessoa")
            return None
        if not t["endossos"]:
            return ("POL-12", f"acima de {_reais(self.perfil['dupla_aprovacao'])} a liberação exige duas pessoas: "
                              f"falta o aval (endorse) da primeira")
        aval = t["endossos"][0]
        avalistas = {aval["pessoa"], aval.get("por_delegacao_de")} - {None}
        if {cadastro["pessoa"], cadastro.get("por_delegacao_de")} & avalistas:
            return ("POL-12", f"{cadastro['pessoa']} já deu o aval deste ticket (diretamente ou por delegação): "
                              f"a segunda aprovação precisa ser de outra pessoa")
        pedidas = [_par(x) for x in c.get("correcoes") or [] if isinstance(x, dict)]
        if aval["decisao"] != decisao or (decisao == "corrigir" and aval["correcoes"] != pedidas):
            return ("POL-12", f"a segunda aprovação precisa ser a mesma decisão avalizada ({aval['decisao']})")
        cadastro["aval"] = {"pessoa": aval["pessoa"], "sessao": aval["sessao"]}
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
