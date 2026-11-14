"""Interface dos conectores de fonte de dados e o que é comum a todos (ADR-011).

Um conector liga a SMA a uma fonte da empresa (ERP simulado, pasta de planilhas, API REST
JSON, servidor MCP por stdio) e entrega os dados no **modelo canônico** (`canonico.py`), com
proveniência por aba. Os agentes não sabem de onde os dados vêm: o gateway MCP continua
oferecendo as mesmas tools, com a mesma allowlist por agente (ADR-004).

    conector.capacidades()        -> {"leitura", "escrita", "competencias", ...}
    conector.testar()             -> diagnóstico: etapas, ok/erro, sem segredos
    conector.ler("2026-09")       -> DadosCanonicos (dados + proveniência)
    conector.corrigir(c, id, acao)-> só se tiver "escrita"; o gateway só chama com aprovação (PROT-APR)

Falhas viram `ErroConector` com mensagem redigida (nunca a credencial, nem o texto do sistema
operacional, que muda entre máquinas): `FonteIndisponivel` (fora do ar, tempo esgotado, HTTP
5xx), `CredencialRecusada` (401/403), `RespostaInvalida` (JSON inválido, recurso ausente),
`DadosInvalidos` (validação do modelo canônico) e `RedeNaoLiberada` (host fora do loopback sem
liberação de um administrador).
"""
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from fin_mas.conectores.canonico import ABAS_OBRIGATORIAS, CANONICO, ConversaoInvalida, conversao_padrao, converter
from fin_mas.env.dataset import Ambiente, mes_no_trimestre
from fin_mas.env.portes import PORTE_PADRAO, PORTES, perfil
from fin_mas.services.redacao import SEGREDO, redigir_texto

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
TEMPO_LIMITE = 10.0
APLICADO_SEM_CONFIRMACAO = "aplicado, confirmação inválida"  # a fonte aceitou a escrita, a releitura falhou


class ErroConector(RuntimeError):
    """Falha de um conector; a mensagem já passou pela redação (e pela remoção do segredo conhecido)."""

    def __init__(self, mensagem: str, segredos=()):
        texto = str(mensagem)
        for s in segredos:
            if s:
                texto = texto.replace(s, SEGREDO)
        super().__init__(redigir_texto(texto)[:400])


class FonteIndisponivel(ErroConector):
    """A fonte não respondeu (conexão recusada, tempo esgotado, erro do servidor)."""


class CredencialRecusada(ErroConector):
    pass


class RespostaInvalida(ErroConector):
    pass


class RedeNaoLiberada(ErroConector, PermissionError):
    pass


class DadosInvalidos(ErroConector):
    def __init__(self, erros: list[str]):
        super().__init__("; ".join(erros[:5]) + (f" (+{len(erros) - 5})" if len(erros) > 5 else ""))
        self.erros = [redigir_texto(e) for e in erros]


class PoliticaRede:
    """Só loopback por padrão; host externo só depois que um administrador o libera (PERM-DAD-REDE)."""

    def __init__(self, liberados=()):
        self.liberados = {str(h).lower() for h in liberados}

    def verificar(self, url: str) -> None:
        partes = urlsplit(url)
        if partes.scheme not in ("http", "https"):
            raise RedeNaoLiberada(f"esquema não permitido: {partes.scheme or '(vazio)'} (use http ou https)")
        host = (partes.hostname or "").lower()
        if not host:
            raise RedeNaoLiberada("URL sem host")
        if host not in LOOPBACK and host not in self.liberados:
            raise RedeNaoLiberada(f"host externo {host} não liberado: só loopback por padrão; um administrador "
                                  "precisa liberá-lo (PERM-DAD-REDE)")


@dataclass
class DadosCanonicos:
    """Uma competência da empresa no modelo canônico."""

    competencia: str
    empresa: dict  # razao_social, sigla, porte, tem_erp
    dados: dict  # aba -> [registro]; valores já convertidos (centavos, AAAA-MM)
    proveniencia: dict  # aba -> URI lógica (sem host, porta ou caminho de máquina)
    avisos: list = field(default_factory=list)


class Conector:
    """Interface. `id` identifica o conector no cadastro; `tipo` é um de TIPOS."""

    tipo = "abstrato"

    def __init__(self, id: str, porte: str | None = None):
        self.id = id
        self.porte = porte

    def capacidades(self) -> set:
        return {"leitura"}

    def testar(self) -> dict:
        raise NotImplementedError

    def ler(self, competencia: str | None) -> DadosCanonicos:
        raise NotImplementedError

    def corrigir(self, competencia: str, lancamento: str, acao: str) -> dict:
        raise ErroConector(f"a fonte {self.id} ({self.tipo}) é só leitura: a correção aprovada precisa ser feita "
                           "na própria fonte")

    def competencia_padrao(self) -> str | None:
        return None

    def descricao(self) -> dict:
        return {"id": self.id, "tipo": self.tipo, "capacidades": sorted(self.capacidades())}

    def dataset(self, competencia: str | None):
        dados = self.ler(competencia)
        return DatasetConector(self, dados)

    def fechar(self) -> None:
        pass


def diagnostico(etapas: list[dict]) -> dict:
    return {"ok": all(e["ok"] for e in etapas), "etapas": etapas}


def etapa(nome: str, ok: bool, detalhe: str = "") -> dict:
    return {"etapa": nome, "ok": ok, "detalhe": redigir_texto(str(detalhe))[:400]}


# ---------------------------------------------------------------- aplicação do mapeamento
class ConectorMapeado(Conector):
    """Conector genérico: lê recursos crus (`ler_recurso`) e aplica o mapeamento confirmado."""

    def __init__(self, id: str, mapeamento: dict | None, porte: str | None = None):
        super().__init__(id, porte)
        self.mapeamento = mapeamento

    def ler_recurso(self, recurso: str, competencia: str | None) -> list[dict]:
        raise NotImplementedError

    def uri(self, recurso: str) -> str:
        return f"conector://{self.id}/{recurso}"

    def ler(self, competencia: str | None) -> DadosCanonicos:
        if not self.mapeamento:
            raise DadosInvalidos([f"conector {self.id}: mapeamento ainda não confirmado"])
        competencia = competencia or self.competencia_padrao()
        cache: dict[str, list] = {}

        def recurso(nome):
            if nome not in cache:
                cache[nome] = self.ler_recurso(nome, competencia)
            return cache[nome]

        return aplicar_mapeamento(self.mapeamento, recurso, competencia, self.uri, porte=self.porte)


def _valor(registro: dict, origem: str):
    """Campo do registro; `a.b` navega em objetos aninhados."""
    if origem in registro:
        return registro[origem]
    atual = registro
    for parte in origem.split("."):
        if not isinstance(atual, dict) or parte not in atual:
            return None
        atual = atual[parte]
    return atual


def aplicar_mapeamento(mapeamento: dict, recurso, competencia: str | None, uri, porte: str | None = None,
                       linha_inicial: int = 1) -> DadosCanonicos:
    """Lê cada aba canônica do recurso mapeado, converte e valida. `recurso(nome)` devolve a lista crua."""
    erros: list[str] = []
    empresa = {}
    for chave, origem in (mapeamento.get("empresa") or {}).items():
        conv = origem.get("conversao") or conversao_padrao(next(c for c in CANONICO["Empresa"] if c[0] == chave)[2])
        bruto = origem["valor"] if "valor" in origem else None
        if origem.get("origem"):
            linhas = recurso(origem["recurso"]) if origem.get("recurso") else []
            bruto = _valor(linhas[0], origem["origem"]) if linhas else None
        try:
            empresa[chave] = converter(bruto, conv)
        except ConversaoInvalida as e:
            erros.append(f"Empresa.{chave}: {e}")
    competencia = competencia or empresa.get("competencia")
    if not competencia:
        erros.append("competência não informada (nem no pedido nem no mapeamento da Empresa)")
    dados, proveniencia = {}, {}
    for aba, spec in mapeamento["abas"].items():
        linhas = recurso(spec["recurso"])
        registros = []
        for n, linha in enumerate(linhas, start=linha_inicial):
            r = {}
            for chave, titulo, tipo, obrigatorio in CANONICO[aba]:
                origem = spec["campos"].get(chave)
                if origem is None:
                    r[chave] = None
                    continue
                bruto = origem["valor"] if "valor" in origem else _valor(linha, origem["origem"])
                try:
                    r[chave] = converter(bruto, origem.get("conversao") or conversao_padrao(tipo))
                except ConversaoInvalida as e:
                    erros.append(f"{aba} registro {n} ({origem.get('origem')}): {e}")
                    r[chave] = None
                    continue
                if r[chave] is None and obrigatorio:
                    erros.append(f"{aba} registro {n}: {chave} é obrigatório ({origem.get('origem')} vazio)")
            r["_linha"] = n
            registros.append(r)
        dados[aba] = registros
        proveniencia[aba] = uri(spec["recurso"])
    for aba in ABAS_OBRIGATORIAS:
        if aba not in dados:
            erros.append(f"aba obrigatória sem mapeamento: {aba}")
    porte = str(empresa.get("porte") or porte or PORTE_PADRAO).strip().lower()
    if porte not in PORTES:
        erros.append(f"porte inválido {porte!r} (use {', '.join(PORTES)})")
    if not erros:
        _validar(dados, porte, erros)
    if erros:
        raise DadosInvalidos(list(dict.fromkeys(erros)))
    empresa = {"razao_social": empresa.get("razao_social") or "Empresa", "sigla": empresa.get("sigla") or "EMPRESA",
               "porte": porte, "tem_erp": empresa.get("tem_erp") if empresa.get("tem_erp") is not None
               else "Realizado" in dados}
    return DadosCanonicos(competencia, empresa, dados, proveniencia)


def _validar(dados, porte, erros) -> None:
    """Mesmas referências que a leitura da planilha confere (pessoas, contas, cargos, unidades)."""
    from fin_mas.env.dataset import RATEIO
    for aba in ("Pessoas", "Produtos", "Orcamento"):
        if not dados.get(aba):
            erros.append(f"{aba}: nenhum registro")
    if erros:
        return
    pessoas = {p["usuario"] for p in dados["Pessoas"]}
    limites = perfil(porte)["limites_alcada"]
    for p in dados["Pessoas"]:
        if p["cargo"] not in limites:
            erros.append(f"Pessoas registro {p['_linha']}: cargo {p['cargo']!r} não existe no porte {porte} "
                         f"(use {', '.join(limites)})")
    contas = {o["conta"] for o in dados["Orcamento"]}
    for lanc in dados["Lancamentos"]:
        for c in ("criador", "aprovador"):
            if lanc[c] not in pessoas:
                erros.append(f"Lancamentos registro {lanc['_linha']}: {c} {lanc[c]!r} não está em Pessoas")
        if lanc["conta"] not in contas:
            erros.append(f"Lancamentos registro {lanc['_linha']}: conta {lanc['conta']!r} não está no Orcamento")
    for p in dados["Produtos"]:
        if p["un"] not in RATEIO:
            erros.append(f"Produtos registro {p['_linha']}: unidade {p['un']!r} (use {', '.join(RATEIO)})")


# ---------------------------------------------------------------- dataset sobre um conector
class DatasetConector:
    """Mesma interface do Dataset sintético e do DatasetPlanilha, alimentada por um conector (sem gabarito)."""

    seed = 0
    plantar = ()

    def __init__(self, conector: Conector, dados: DadosCanonicos):
        self.conector = conector
        self.correcoes: list = []
        self.sem_confirmacao = None  # erro da releitura depois de uma escrita aceita: o dado em memória é o de antes
        self._carregar(dados)

    def _carregar(self, d: DadosCanonicos) -> None:
        self.competencia = d.competencia
        self.porte = d.empresa["porte"]
        self.razao_social = d.empresa["razao_social"]
        self.entidade = d.empresa["sigla"]
        self.tem_erp = bool(d.empresa["tem_erp"])
        self._proveniencia = dict(d.proveniencia)
        dados = d.dados
        self.perfil = {**perfil(self.porte), "tem_erp": self.tem_erp}
        self.perfil["pessoas"] = {p["usuario"]: p["cargo"] for p in dados["Pessoas"]}
        self.perfil["fonte_primaria"] = "ERP" if self.tem_erp else "planilha"
        self.produtos = [{k: p[k] for k in ("id", "un", "qtd", "preco", "custo_variavel_unit")} for p in dados["Produtos"]]
        self.custos_fixos = [{"centro": c["centro"], "valor": c["valor"]} for c in dados["CustosFixos"]]
        self.orcamento = [{k: o[k] for k in ("conta", "orcado_trimestre", "orcado_acumulado", "realizado_acumulado")}
                          for o in dados["Orcamento"]]
        self.observacoes = {o["conta"]: o["observacao"] for o in dados["Orcamento"] if o.get("observacao")}
        self.lancamentos = [{k: x[k] for k in ("id", "competencia", "conta", "fornecedor", "documento", "valor",
                                               "criador", "aprovador")}
                            for x in dados["Lancamentos"] if (x.get("situacao") or "ativo") == "ativo"]
        self.realizado_erp = {r["conta"]: r["realizado_acumulado"] for r in dados.get("Realizado", [])}
        self._historico = {}
        for h in dados.get("Historico", []):
            self._historico.setdefault(h["conta"], []).append(
                {"competencia": h["competencia"], "mes_no_trimestre": mes_no_trimestre(h["competencia"]),
                 "orcado": h["orcado"], "realizado": h["realizado"]})
        self.gold = {"meses_decorridos": mes_no_trimestre(self.competencia)}  # dados reais não têm gabarito

    def historico(self) -> dict:
        return {conta: [dict(x) for x in serie] for conta, serie in self._historico.items()}

    def proveniencia(self, aba: str) -> str:
        return "+".join(self._proveniencia.get(a, f"conector://{self.conector.id}/{a}") for a in aba.split("+"))

    def corrigir(self, lancamento: str, acao: str) -> dict:
        """Correção aprovada (o gateway já conferiu o ticket): escrita na fonte e releitura da fonte."""
        if not any(x["id"] == lancamento for x in self.lancamentos):
            raise ValueError(f"lançamento desconhecido: {lancamento}")
        registro = self.conector.corrigir(self.competencia, lancamento, acao)
        registro = {"lancamento": lancamento, "acao": acao, "detalhe": registro.get("detalhe") or f"{lancamento} {acao}"}
        try:
            self._carregar(self.conector.ler(self.competencia))  # a fonte é a verdade: relê depois de escrever
        except (ErroConector, ValueError, LookupError, TypeError) as erro:
            # a escrita foi aceita pela fonte: o efeito ocorreu e não pode ser repetido nem dado como não executado;
            # o que falhou foi a confirmação. Fica registrado assim (trace e resposta). O dado em memória continua o
            # de antes da correção: a reavaliação do AG-CIN vê o achado de novo e mantém o veto (falha fechada).
            registro.update(situacao=APLICADO_SEM_CONFIRMACAO, confirmacao=f"releitura falhou: {erro}"[:300],
                            detalhe=f"{registro['detalhe']} ({APLICADO_SEM_CONFIRMACAO}: a releitura da fonte falhou)")
            self.sem_confirmacao = erro
        self.correcoes.append(registro)
        return registro


class DatasetIndisponivel:
    """A fonte não respondeu: o sistema sobe (porte e competência configurados), mas toda leitura falha
    explicitamente com o motivo, e cada nova chamada tenta a fonte outra vez."""

    seed = 0
    plantar = ()

    def __init__(self, conector: Conector, competencia: str, porte: str, erro: ErroConector):
        self.conector, self.competencia, self.porte, self.erro = conector, competencia, porte, erro
        from fin_mas.env.dataset import ENTIDADE
        self.entidade = (getattr(conector, "config", None) or {}).get("sigla") or ENTIDADE
        self.razao_social = ""
        self.perfil = {**perfil(porte), "tem_erp": True}
        self.gold = {"meses_decorridos": mes_no_trimestre(competencia)}
        self.correcoes: list = []

    def __getattr__(self, nome):
        if nome in ("produtos", "custos_fixos", "orcamento", "lancamentos", "realizado_erp", "observacoes"):
            raise FonteIndisponivel(f"fonte {self.conector.id} indisponível: {self.erro}")
        raise AttributeError(nome)

    def historico(self):
        raise FonteIndisponivel(f"fonte {self.conector.id} indisponível: {self.erro}")

    def proveniencia(self, aba: str) -> str:
        return f"conector://{self.conector.id}/{aba}"

    def corrigir(self, lancamento, acao):
        raise FonteIndisponivel(f"fonte {self.conector.id} indisponível: {self.erro}")


class AmbienteConector(Ambiente):
    """Competências lidas de um conector, sob demanda e guardadas; fonte fora do ar não trava o sistema."""

    def __init__(self, conector: Conector, competencia: str | None = None, porte: str | None = None):
        principal = competencia or conector.competencia_padrao()
        if not principal:
            raise ValueError("informe a competência principal da fonte (AAAA-MM)")
        super().__init__(0, agenda={principal: ()}, porte=porte or conector.porte or PORTE_PADRAO)
        self.conector = conector
        self.fonte = "conector"

    def dataset(self, competencia: str | None = None):
        c = competencia or self.principal
        if c in self._ds:
            return self._ds[c]
        try:
            ds = self.conector.dataset(c)
        except FonteIndisponivel as erro:
            return DatasetIndisponivel(self.conector, c, self.porte, erro)
        self._ds[c] = ds
        return ds

    def descricao_fonte(self) -> dict:
        return self.conector.descricao()

    def fechar(self) -> None:
        self.conector.fechar()
