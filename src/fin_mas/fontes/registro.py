"""Cadastro das fontes de dados da plataforma (ADR-011): conectores, mapeamentos, rede, envios.

Fica num `ArquivoSelado` (`fontes.json`) ao lado do cofre de credenciais (`cofre.json`), na pasta de
fontes da instalação; com empresas (IAM-09), um registro por empresa em `dados/<empresa>/fontes`, com cofre
e nomes de credencial próprios (`conector:<id>@<empresa>`). Regras:

- **credencial**: entra uma vez no cadastro, vai para o cofre e nunca volta (a listagem só diz se há
  uma); fica vinculada ao host:porta da URL do momento em que foi guardada. Trocou a URL, a
  credencial deixa de ser enviada até ser informada de novo;
- **rede**: só loopback por padrão; host externo só depois que uma pessoa com PERM-DAD-REDE (o
  administrador) o libera; liberar e revogar ficam na trilha de acesso;
- **mapeamento**: o entendimento propõe; só vale depois que uma pessoa com PERM-DAD-CONECTAR o
  confirma (com nome e hora), e a confirmação passa pela validação determinística. A confirmação
  guarda a **impressão digital** da fonte (colunas de cada recurso mapeado, classe e ordem de grandeza
  da amostra de cada coluna); a cada ativação e a cada reinício a fonte é relida e, se a impressão
  divergir (coluna renomeada, sumida ou nova, tipo trocado, unidade trocada como reais -> centavos),
  a confirmação deixa de valer, a fonte volta a "a confirmar" e a ativação falha com o motivo, em vez
  de entregar dado errado;
- **caminhos**: pelo dashboard só se usam arquivos dentro da pasta de fontes; o MCP cadastrável pelo
  dashboard é só o servidor de Excel embutido (comando montado aqui, nunca vindo do navegador);
- toda ação vai para a trilha de acesso com a pessoa, sem valores de credencial.
"""
import hashlib
import json
import math
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

from fin_mas.conectores import TIPOS
from fin_mas.conectores.base import AmbienteConector, ErroConector, FonteIndisponivel, LOOPBACK, PoliticaRede
from fin_mas.conectores.canonico import CANONICO, converter, ConversaoInvalida, validar_mapeamento
from fin_mas.env.portes import PORTES
from fin_mas.fontes import entendimento, planilha
from fin_mas.services.cofre import Cofre, caminho_padrao
from fin_mas.services.redacao import redigir
from fin_mas.services.selado import ArquivoSelado

VERSAO = 1
ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,39}$")
HOST = re.compile(r"^[a-z0-9.-]{1,253}(:\d{1,5})?$")
EMBUTIDO = "erp-simulado"
CAMPOS_CONFIG = {
    "rest": {"url_base", "autenticacao", "openapi", "recursos", "tempo_limite", "porte", "competencia", "escrita"},
    "planilhas": {"pasta", "porte"},
    "planilha": {"arquivo", "porte", "competencia"},
    "mcp": {"pasta", "competencia", "porte", "tempo_limite"},
    "erp_simulado": {"seed", "porte"},
}
MAX_ENVIOS = 200
LIMITE_UPLOAD = 5 * 1024 * 1024


class RecusaFonte(ValueError):
    """Pedido recusado (vira 400/422 na API) com motivo legível."""

    def __init__(self, motivo: str, status: int = 400, erros: list | None = None):
        super().__init__(motivo)
        self.status, self.erros = status, erros or []


class FonteMudou(RecusaFonte):
    """A fonte não tem mais a impressão digital da confirmação: o mapeamento confirmado deixou de valer (409)."""


def _perfil_coluna(valores) -> dict | None:
    """Classe e ordem de grandeza da amostra de uma coluna (None: coluna sem valor na amostra)."""
    if not valores:
        return None
    numeros = [v for v in valores if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)]
    if len(numeros) == len(valores):
        absolutos = sorted(abs(v) for v in numeros if v)
        return {"classe": "numero", "escala": math.floor(math.log10(absolutos[len(absolutos) // 2])) if absolutos else None}
    textos = [v for v in valores if isinstance(v, str)]
    return {"classe": "texto" if len(textos) == len(valores) else "misto", "escala": None}


def perfil_da_estrutura(estrutura: dict) -> dict:
    """{recurso: {coluna: {classe, escala}}} das colunas com valor na amostra."""
    perfil = {}
    for r in estrutura.get("recursos", []):
        colunas = {}
        for c in r.get("campos", []):
            p = _perfil_coluna(c.get("_valores") or [])
            if p is not None:
                colunas[c["nome"]] = p
        perfil[r["nome"]] = colunas
    return perfil


def _recursos_do_mapeamento(mapeamento: dict) -> set:
    return {spec.get("recurso") for spec in (mapeamento.get("abas") or {}).values() if spec.get("recurso")} | \
        {e.get("recurso") for e in (mapeamento.get("empresa") or {}).values() if e.get("recurso")}


def divergencias(antes: dict, agora: dict) -> list[str]:
    """O que mudou na fonte desde a impressão `antes` (vazio: a fonte é a mesma que a pessoa confirmou)."""
    saida = []
    for recurso, colunas in sorted(antes.items()):
        novas = agora.get(recurso)
        if novas is None:
            saida.append(f"{recurso}: recurso não encontrado na fonte")
            continue
        sumiram, apareceram = sorted(set(colunas) - set(novas)), sorted(set(novas) - set(colunas))
        if sumiram or apareceram:
            saida.append(f"{recurso}: colunas mudaram (sumiram {sumiram}, apareceram {apareceram})")
        for col in sorted(set(colunas) & set(novas)):
            a, b = colunas[col], novas[col]
            if a["classe"] != b["classe"]:
                saida.append(f"{recurso}.{col}: tipo mudou ({a['classe']} -> {b['classe']})")
            elif a["escala"] is not None and b["escala"] is not None and abs(a["escala"] - b["escala"]) >= 2:
                saida.append(f"{recurso}.{col}: escala mudou (ordem de grandeza 10^{a['escala']} -> 10^{b['escala']}; "
                             "unidade trocada?)")
    return saida


def _digest(dados) -> str:
    return hashlib.sha256(json.dumps(dados, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


class RegistroFontes:
    def __init__(self, pasta=None, registrar=None, relogio=time.time, empresa: str | None = None):
        self.pasta = Path(pasta) if pasta else None
        self.empresa = empresa  # IAM-09: registro, pasta e credenciais desta empresa (dados/<empresa>/fontes)
        self._registrar = registrar
        self.relogio = relogio
        self._arq = ArquivoSelado(self.pasta / "fontes.json" if self.pasta else None, "fontes", VERSAO,
                                  {"conectores": {}, "mapeamentos": {}, "envios": [], "rede": {}, "ativo": None})
        # credenciais no cofre selado da plataforma (services/cofre.py), fora da pasta de dados: na pasta de chaves
        self.cofre = Cofre(caminho_padrao(self.pasta) if self.pasta else None, relogio=relogio)
        if self.pasta:
            for sub in ("planilhas", "recebidas"):
                (self.pasta / sub).mkdir(parents=True, exist_ok=True)

    # ---- apoio --------------------------------------------------------------------------------
    def credencial(self, cid: str) -> str:
        """Nome da credencial do conector no cofre; com empresa, o nome leva a empresa (`conector:<id>@<empresa>`)."""
        return f"conector:{cid}@{self.empresa}" if self.empresa else f"conector:{cid}"

    def _trilha(self, evento, ator, resultado="ok", **campos):
        if self._registrar is not None:
            if self.empresa:
                campos.setdefault("empresa", self.empresa)
            self._registrar(evento, ator, resultado, **redigir(campos))

    def _dados(self) -> dict:
        return self._arq.ler()

    def _dentro(self, relativo: str) -> Path:
        if self.pasta is None:
            raise RecusaFonte("servidor sem pasta de fontes")
        alvo = (self.pasta / str(relativo)).resolve()
        if self.pasta.resolve() not in (alvo, *alvo.parents):
            raise RecusaFonte(f"caminho fora da pasta de fontes: {relativo}")
        return alvo

    def politica(self) -> PoliticaRede:
        return PoliticaRede(self._dados()["rede"])

    # ---- leitura pública (nunca credenciais) ------------------------------------------------
    def listar(self) -> dict:
        d = self._dados()
        liberados = d["rede"]
        conectores = [{"id": EMBUTIDO, "nome": "ERP simulado (dados sintéticos com gabarito)", "tipo": "erp_simulado",
                       "embutido": True, "config": {}, "tem_credencial": False, "rede": "sem rede",
                       "mapeamento": {"situacao": "não precisa"}, "ativo": d["ativo"] in (None, EMBUTIDO)}]
        for c in d["conectores"].values():
            conectores.append(self._publico(c, d, liberados))
        return {"conectores": conectores, "ativo": d["ativo"] or EMBUTIDO,
                "rede": [{"host": h, **v} for h, v in sorted(liberados.items())],
                "envios": list(reversed(d["envios"]))[:50], "abas_canonicas": {
                    aba: [{"campo": k, "titulo": t, "tipo": tp, "obrigatorio": o} for k, t, tp, o in campos]
                    for aba, campos in CANONICO.items()}}

    def _publico(self, c, d, liberados) -> dict:
        tem = self.cofre.existe(self.credencial(c['id']))
        saida = {k: c[k] for k in ("id", "nome", "tipo", "criado_por", "criado_em", "atualizado_por", "atualizado_em")
                 if k in c}
        saida["config"] = redigir({k: v for k, v in c["config"].items()})
        saida["tem_credencial"] = tem
        if c["tipo"] == "rest":
            netloc = urlsplit(c["config"]["url_base"]).netloc.lower()
            host = (urlsplit(c["config"]["url_base"]).hostname or "").lower()
            saida["credencial_vinculada"] = tem and c.get("credencial_host") == netloc
            saida["rede"] = "loopback" if host in LOOPBACK else \
                "liberado por administrador" if host in liberados else "bloqueado: aguarda liberação de um administrador"
        else:
            saida["rede"] = "sem rede"
        m = d["mapeamentos"].get(c["id"]) or {}
        if m.get("confirmado"):
            conf = m["confirmado"]
            saida["mapeamento"] = {"situacao": "confirmado", "por": conf["por"], "em": conf["em"],
                                   "digest": conf["digest"], "competencia": conf.get("competencia")}
        elif m.get("invalidado"):
            inv = m["invalidado"]
            saida["mapeamento"] = {"situacao": "a confirmar: a fonte mudou desde a confirmação",
                                   "em": inv["em"], "motivos": inv["motivos"], "digest_anterior": inv["digest"]}
        elif m.get("proposta"):
            saida["mapeamento"] = {"situacao": "proposto, aguardando confirmação"}
        else:
            saida["mapeamento"] = {"situacao": "não precisa" if c["tipo"] == "planilhas" else "nenhum"}
        saida["ativo"] = d["ativo"] == c["id"]
        return saida

    # ---- cadastro ---------------------------------------------------------------------------
    def cadastrar(self, ator: str, pedido: dict) -> dict:
        cid, tipo = pedido.get("id"), pedido.get("tipo")
        if not isinstance(cid, str) or not ID.match(cid) or cid == EMBUTIDO:
            raise RecusaFonte("id: de 2 a 40 letras minúsculas, números ou hífen (e não 'erp-simulado')")
        if tipo not in TIPOS or tipo == "erp_simulado":
            raise RecusaFonte(f"tipo: um de {', '.join(t for t in TIPOS if t != 'erp_simulado')}")
        config = pedido.get("config") or {}
        if not isinstance(config, dict):
            raise RecusaFonte("config precisa ser um objeto")
        estranhos = set(config) - CAMPOS_CONFIG[tipo]
        if estranhos:
            raise RecusaFonte(f"campos de configuração não aceitos para {tipo}: {', '.join(sorted(estranhos))}")
        self._validar_config(tipo, config)
        credencial = pedido.get("credencial")
        if credencial is not None and (not isinstance(credencial, str) or tipo != "rest"):
            raise RecusaFonte("credencial: texto, e só para conectores REST")
        agora = self.relogio()
        with self._arq.transacao() as d:
            antigo = d["conectores"].get(cid)
            if antigo and antigo["tipo"] != tipo:
                raise RecusaFonte(f"{cid} já existe com o tipo {antigo['tipo']}")
            registro = {**(antigo or {"criado_por": ator, "criado_em": agora}), "id": cid, "tipo": tipo,
                        "nome": str(pedido.get("nome") or cid)[:80], "config": config,
                        "atualizado_por": ator, "atualizado_em": agora}
            if credencial:
                registro["credencial_host"] = urlsplit(config["url_base"]).netloc.lower()
            if antigo and antigo.get("config") != config:  # outra configuração: o mapeamento confirmado deixa de valer
                d["mapeamentos"].pop(cid, None)
            d["conectores"][cid] = registro
        if credencial:
            self.cofre.guardar(self.credencial(cid), credencial, str(ator))
            self._trilha("credencial_guardada", ator, credencial=self.credencial(cid))
        self._trilha("conector_cadastrado", ator, conector=cid, tipo=tipo, novo=antigo is None,
                     credencial="informada" if credencial else "não informada")
        return self._publico(registro, self._dados(), self._dados()["rede"])

    def _validar_config(self, tipo, config) -> None:
        if tipo == "rest":
            url = str(config.get("url_base") or "")
            partes = urlsplit(url)
            if partes.scheme not in ("http", "https") or not partes.hostname or partes.username or partes.password:
                raise RecusaFonte("url_base: http(s)://host[:porta], sem usuário e senha na URL")
            auth = (config.get("autenticacao") or {}).get("tipo", "nenhuma")
            if auth not in ("nenhuma", "bearer", "cabecalho", "query"):
                raise RecusaFonte("autenticacao.tipo: nenhuma, bearer, cabecalho ou query")
            for chave in ("openapi",):
                if config.get(chave) and ("://" in str(config[chave]) or str(config[chave]).startswith("//")):
                    raise RecusaFonte(f"{chave}: caminho relativo à URL base")
            for nome, spec in (config.get("recursos") or {}).items():
                if not isinstance(spec, dict) or "://" in str(spec.get("caminho", "")):
                    raise RecusaFonte(f"recurso {nome}: caminho relativo à URL base")
            tempo = config.get("tempo_limite", 10)
            if not isinstance(tempo, (int, float)) or not 0.5 <= tempo <= 60:
                raise RecusaFonte("tempo_limite: de 0,5 a 60 segundos")
        elif tipo in ("planilhas", "mcp"):
            self._dentro(config.get("pasta") or "planilhas")
        elif tipo == "planilha":
            alvo = self._dentro(config.get("arquivo") or "")
            if alvo.suffix.lower() != ".xlsx":
                raise RecusaFonte("arquivo: um .xlsx da pasta de fontes")
        if config.get("porte") not in (None, *PORTES):
            raise RecusaFonte(f"porte: um de {', '.join(PORTES)}")
        if config.get("competencia") is not None:
            try:
                converter(config["competencia"], "competencia")
            except ConversaoInvalida as e:
                raise RecusaFonte(f"competencia: {e}") from None

    def remover(self, ator: str, cid: str) -> None:
        with self._arq.transacao() as d:
            if cid not in d["conectores"]:
                raise RecusaFonte(f"conector desconhecido: {cid}", 404)
            d["conectores"].pop(cid)
            d["mapeamentos"].pop(cid, None)
            if d["ativo"] == cid:
                d["ativo"] = None
        if self.cofre.remover(self.credencial(cid), str(ator)):
            self._trilha("credencial_removida", ator, credencial=self.credencial(cid))
        self._trilha("conector_removido", ator, conector=cid)

    # ---- rede (administrador) -----------------------------------------------------------------
    def liberar_host(self, ator: str, host: str, liberar: bool = True) -> dict:
        host = str(host or "").strip().lower()
        if not HOST.match(host) or host.split(":")[0] in LOOPBACK:
            raise RecusaFonte("host: nome ou IP externo (loopback já é permitido)")
        nome = host.split(":")[0]
        with self._arq.transacao() as d:
            if liberar:
                d["rede"][nome] = {"por": ator, "em": self.relogio()}
            else:
                d["rede"].pop(nome, None)
        self._trilha("rede_liberada" if liberar else "rede_revogada", ator, host=nome)
        return {"host": nome, "liberado": liberar}

    # ---- conector vivo ---------------------------------------------------------------------
    def _registro(self, cid) -> dict:
        c = self._dados()["conectores"].get(cid)
        if c is None:
            raise RecusaFonte(f"conector desconhecido: {cid}", 404)
        return c

    def construir(self, cid: str, mapeamento: dict | None = "confirmado"):
        """Instância do conector, com a credencial do cofre e o mapeamento confirmado (se houver)."""
        from fin_mas.conectores.mcp_cliente import ConectorMCP, comando_excel
        from fin_mas.conectores.planilhas import ConectorPastaPlanilhas, ConectorPlanilha
        from fin_mas.conectores.rest import ConectorREST
        c = self._registro(cid)
        if mapeamento == "confirmado":
            mapeamento = ((self._dados()["mapeamentos"].get(cid) or {}).get("confirmado") or {}).get("mapeamento")
        cfg = dict(c["config"])
        if c["tipo"] == "rest":
            return ConectorREST(cid, cfg, segredo=self.cofre.ler(self.credencial(cid)), mapeamento=mapeamento,
                                politica=self.politica(), host_credencial=c.get("credencial_host") or "-")
        if c["tipo"] == "planilhas":
            return ConectorPastaPlanilhas(cid, self._dentro(cfg.get("pasta") or "planilhas"), porte=cfg.get("porte"))
        if c["tipo"] == "planilha":
            return ConectorPlanilha(cid, self._dentro(cfg["arquivo"]), mapeamento=mapeamento, porte=cfg.get("porte"))
        if c["tipo"] == "mcp":
            return ConectorMCP(cid, {**cfg, "comando": comando_excel(self._dentro(cfg.get("pasta") or "planilhas"))},
                               mapeamento=mapeamento)
        raise RecusaFonte(f"tipo sem construtor: {c['tipo']}")

    def testar(self, ator: str, cid: str) -> dict:
        if cid == EMBUTIDO:
            from fin_mas.conectores.simulado import ConectorSimulado
            return ConectorSimulado().testar()
        try:
            diag = self.construir(cid, mapeamento=None).testar()
        except (ValueError, ErroConector) as e:
            diag = {"ok": False, "etapas": [{"etapa": "configuração", "ok": False, "detalhe": str(e)}]}
        self._trilha("conector_testado", ator, "ok" if diag["ok"] else "falha", conector=cid)
        return diag

    def entender(self, ator: str, cid: str, competencia: str | None = None, llm: dict | None = None,
                 contexto: dict | None = None) -> dict:
        from fin_mas.conectores import descoberta
        conector = self.construir(cid, mapeamento=None)
        competencia = competencia or conector.competencia_padrao()
        try:
            estrutura = descoberta.estrutura_de(conector, competencia, contexto)
        except ErroConector as e:
            self._trilha("fonte_entendida", ator, "falha", conector=cid, motivo=str(e))
            raise RecusaFonte(f"não foi possível ler a fonte: {e}", 422) from None
        resultado = entendimento.entender(estrutura, competencia)
        detectada = competencia or _competencia_detectada(estrutura, resultado["sugestao"])
        if detectada and detectada != competencia:
            resultado["qualidade"] = entendimento.qualidade(estrutura, resultado["sugestao"]["mapeamento"], detectada)
        if llm:
            extra = entendimento.sugerir_com_llm(estrutura, resultado["sugestao"], llm)
            resultado["llm"] = extra
            for a in extra["aceitas"]:
                linha = next(s for s in resultado["sugestao"]["sugestoes"] if (s["aba"], s["campo"]) == (a["aba"], a["campo"]))
                linha.update({k: a[k] for k in ("recurso", "origem", "conversao", "confianca", "motivo",
                                                 "fonte_sugestao")}, revisar=True)
        resultado["competencia"] = detectada
        recursos = {r["nome"]: sorted(c["nome"] for c in r["campos"]) for r in estrutura["recursos"]}
        with self._arq.transacao() as d:
            if conector.tipo in ("rest", "mcp") and cid in d["conectores"]:  # recursos descobertos no contrato
                cfg = d["conectores"][cid]["config"]
                for chave in ("recursos", "escrita"):
                    if conector.config.get(chave) and chave in CAMPOS_CONFIG[conector.tipo] and not cfg.get(chave):
                        cfg[chave] = conector.config[chave]
                if conector.tipo == "mcp":
                    d["conectores"][cid]["recursos_mcp"] = conector.config.get("recursos")
            d["mapeamentos"].setdefault(cid, {})["proposta"] = {
                "recursos": recursos, "competencia": detectada, "em": self.relogio(), "por": ator,
                "perfil": perfil_da_estrutura(estrutura), "competencia_lida": competencia,
                "contexto": estrutura.get("contexto") or contexto}
        self._trilha("fonte_entendida", ator, conector=cid, recursos=len(recursos),
                     llm=bool(llm), sugestoes=sum(1 for s in resultado["sugestao"]["sugestoes"] if s["origem"]))
        resultado["recursos_campos"] = recursos
        return resultado

    def confirmar(self, ator: str, cid: str, sugestoes: list, competencia: str | None = None) -> dict:
        d0 = self._dados()
        proposta = (d0["mapeamentos"].get(cid) or {}).get("proposta")
        if proposta is None:
            raise RecusaFonte("entenda a fonte antes de confirmar o mapeamento", 409)
        if not isinstance(sugestoes, list) or not all(isinstance(s, dict) for s in sugestoes):
            raise RecusaFonte("sugestoes: lista de linhas {aba, campo, recurso, origem, conversao}")
        linhas = []
        for s in sugestoes:
            if s.get("aba") not in CANONICO or not any(c[0] == s.get("campo") for c in CANONICO[s["aba"]]):
                raise RecusaFonte(f"campo canônico inexistente: {s.get('aba')}.{s.get('campo')}", 422)
            tipo = next(c[2] for c in CANONICO[s["aba"]] if c[0] == s["campo"])
            linha = {"aba": s["aba"], "campo": s["campo"], "tipo": tipo, "recurso": s.get("recurso"),
                     "origem": s.get("origem") or None, "conversao": s.get("conversao"), "fonte_sugestao": "pessoa"}
            if s.get("valor") not in (None, "") and not linha["origem"]:
                linha["valor"] = s["valor"]
            linhas.append(linha)
        mapeamento = entendimento.mapeamento_de(linhas, minimo=0)
        recursos = {r: set(c) for r, c in proposta["recursos"].items()}
        erros = validar_mapeamento(mapeamento, recursos)
        if erros:
            self._trilha("mapeamento_confirmado", ator, "negado", conector=cid, erros=len(erros))
            raise RecusaFonte("o mapeamento não passa na validação", 422, erros)
        competencia = competencia or proposta.get("competencia")
        perfil = proposta.get("perfil") or {}
        impressao = {r: perfil.get(r, {}) for r in sorted(_recursos_do_mapeamento(mapeamento))}
        conf = {"mapeamento": mapeamento, "por": ator, "em": self.relogio(), "digest": _digest(mapeamento),
                "competencia": competencia, "impressao": impressao, "competencia_lida": proposta.get("competencia_lida"),
                "contexto": proposta.get("contexto")}
        with self._arq.transacao() as d:
            if cid not in d["conectores"]:
                raise RecusaFonte(f"conector desconhecido: {cid}", 404)
            d["mapeamentos"].setdefault(cid, {})["confirmado"] = conf
            d["mapeamentos"][cid].pop("invalidado", None)
        self._trilha("mapeamento_confirmado", ator, conector=cid, digest=conf["digest"],
                     abas=sorted(mapeamento["abas"]), impressao=_digest(impressao))
        return {k: conf[k] for k in ("por", "em", "digest", "competencia")} | {"abas": sorted(mapeamento["abas"])}

    def fabrica(self, ator: str, cid: str, competencia: str | None = None):
        """Confere a fonte (uma leitura completa) e devolve a fábrica de ambientes para o reinício."""
        if cid == EMBUTIDO:
            with self._arq.transacao() as d:
                d["ativo"] = None
            self._trilha("fonte_ativada", ator, conector=cid)
            return None
        c = self._registro(cid)
        m = (self._dados()["mapeamentos"].get(cid) or {}).get("confirmado")
        if c["tipo"] != "planilhas" and m is None:
            raise RecusaFonte("o mapeamento desta fonte ainda não foi confirmado por uma pessoa", 409)
        competencia = competencia or (m or {}).get("competencia") or c["config"].get("competencia")

        def montar():  # a cada montagem (ativação e reinícios), a confirmação vigente e a impressão da fonte
            atual = (self._dados()["mapeamentos"].get(cid) or {}).get("confirmado")
            if c["tipo"] != "planilhas" and atual is None:
                raise FonteMudou("o mapeamento desta fonte não está mais confirmado (a fonte mudou?): entenda e "
                                 "confirme de novo", 409)
            if atual is not None and atual.get("impressao") is not None:
                self.conferir_impressao(ator, cid, atual)
            conector = self.construir(cid)
            if c["tipo"] == "mcp" and c.get("recursos_mcp"):
                conector.config["recursos"] = c["recursos_mcp"]
            return AmbienteConector(conector, competencia=competencia or conector.competencia_padrao(),
                                    porte=c["config"].get("porte"))

        try:
            amb = montar()
            ds = amb.conector.dataset(amb.principal)
        except FonteMudou:
            raise
        except FonteIndisponivel as e:
            self._trilha("fonte_ativada", ator, "falha", conector=cid, motivo=str(e))
            raise RecusaFonte(f"fonte indisponível: {e}", 422) from None
        except (ErroConector, ValueError, LookupError) as e:
            self._trilha("fonte_ativada", ator, "falha", conector=cid, motivo=str(e))
            raise RecusaFonte(f"a fonte não passou na leitura: {e}", 422, list(getattr(e, "erros", []))) from None
        finally:
            if "amb" in locals():
                amb.fechar()
        with self._arq.transacao() as d:
            d["ativo"] = cid
        self._trilha("fonte_ativada", ator, conector=cid, competencia=ds.competencia)
        return montar

    def conferir_impressao(self, ator: str, cid: str, conf: dict) -> None:
        """Relê a fonte e compara com a impressão digital da confirmação; divergiu, a confirmação deixa de valer
        (a fonte volta a "a confirmar") e a montagem falha com o motivo (ADR-011): nunca dado lido com o
        mapeamento de uma fonte que já não é a mesma."""
        from fin_mas.conectores import descoberta
        conector = self.construir(cid, mapeamento=None)
        try:
            estrutura = descoberta.estrutura_de(conector, conf.get("competencia_lida"), conf.get("contexto"))
        finally:
            if hasattr(conector, "fechar"):
                conector.fechar()
        mudou = divergencias(conf["impressao"], perfil_da_estrutura(estrutura))
        if not mudou:
            return
        with self._arq.transacao() as d:
            m = d["mapeamentos"].get(cid) or {}
            if (m.get("confirmado") or {}).get("digest") == conf["digest"]:
                m.pop("confirmado")
                m["invalidado"] = {"em": self.relogio(), "motivos": mudou[:10], "digest": conf["digest"]}
                d["mapeamentos"][cid] = m
            if d["ativo"] == cid:
                d["ativo"] = None
        self._trilha("mapeamento_invalidado", ator, "negado", regra="ADR-011", conector=cid, digest=conf["digest"],
                     motivos=mudou[:10])
        raise FonteMudou("a fonte mudou desde a confirmação do mapeamento (" + "; ".join(mudou[:3]) + "): entenda e "
                         "confirme de novo antes de ativar", 409, mudou)

    # ---- envios de planilha -----------------------------------------------------------------------
    def receber_planilha(self, ator: str, nome: str, conteudo: bytes) -> dict:
        nome = Path(str(nome or "planilha.xlsx")).name
        if not nome.lower().endswith(".xlsx") or len(conteudo) > LIMITE_UPLOAD or not conteudo:
            raise RecusaFonte("envie um .xlsx de até 5 MB")
        if not re.fullmatch(r"[\w .()-]{1,80}\.xlsx", nome, re.UNICODE):
            nome = "planilha.xlsx"
        recebida = self._dentro("recebidas") / nome
        recebida.write_bytes(conteudo)
        registro = {"quando": self.relogio(), "por": ator, "arquivo": nome}
        try:
            ds = planilha.ler(recebida)
        except planilha.ModeloInvalido as e:
            registro.update(ok=False, modelo=False, erros=e.erros[:5])
        except Exception as e:  # não abre como xlsx
            recebida.unlink(missing_ok=True)
            registro.update(ok=False, modelo=False, erros=[f"não foi possível ler a planilha: {type(e).__name__}"])
            self._anotar(registro)
            raise RecusaFonte("arquivo não é uma planilha .xlsx legível", 422, registro["erros"]) from None
        else:
            destino = self._dentro("planilhas") / f"competencia_{ds.competencia}.xlsx"
            destino.write_bytes(conteudo)
            recebida.unlink(missing_ok=True)
            registro.update(ok=True, modelo=True, competencia=ds.competencia, porte=ds.porte,
                            destino=f"planilhas/{destino.name}", conector="planilhas", erros=[])
            with self._arq.transacao() as d:
                d["conectores"].setdefault("planilhas", {
                    "id": "planilhas", "tipo": "planilhas", "nome": "Pasta de planilhas (modelo da SMA)",
                    "config": {"pasta": "planilhas"}, "criado_por": ator, "criado_em": self.relogio(),
                    "atualizado_por": ator, "atualizado_em": self.relogio()})
        if not registro["ok"]:  # fora do modelo: vira uma fonte para entender e mapear
            cid = "planilha-" + (re.sub(r"[^a-z0-9]+", "-", Path(nome).stem.lower()).strip("-")[:28] or "enviada")
            with self._arq.transacao() as d:
                anterior = d["conectores"].get(cid)
                d["conectores"][cid] = {**(anterior or {"criado_por": ator, "criado_em": self.relogio()}),
                                        "id": cid, "tipo": "planilha", "nome": f"Planilha {nome}",
                                        "config": {"arquivo": f"recebidas/{nome}"}, "atualizado_por": ator,
                                        "atualizado_em": self.relogio()}
                d["mapeamentos"].pop(cid, None)
            registro.update(destino=f"recebidas/{nome}", conector=cid,
                            mensagem="fora do modelo da SMA: use Entender para mapear as colunas")
        self._anotar(registro)
        self._trilha("planilha_recebida", ator, "ok" if registro["ok"] else "fora_do_modelo", arquivo=nome,
                     conector=registro.get("conector"))
        return registro

    def _anotar(self, registro) -> None:
        with self._arq.transacao() as d:
            d["envios"] = (d["envios"] + [registro])[-MAX_ENVIOS:]


def _competencia_detectada(estrutura, sugestao) -> str | None:
    """Competência da fonte pela sugestão de Empresa.competencia (valor da amostra), se houver."""
    s = next((x for x in sugestao["sugestoes"] if (x["aba"], x["campo"]) == ("Empresa", "competencia") and x["origem"]),
             None)
    if not s:
        return None
    r = next((r for r in estrutura["recursos"] if r["nome"] == s["recurso"]), None)
    valores = next((c.get("_valores") for c in (r or {}).get("campos", []) if c["nome"] == s["origem"]), None) or []
    try:
        return converter(valores[0], s["conversao"]) if valores else None
    except ConversaoInvalida:
        return None
