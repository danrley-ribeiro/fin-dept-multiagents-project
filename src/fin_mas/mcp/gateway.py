"""Servidores MCP sobre a fonte de dados da empresa (ADR-004).

A fonte é o dataset sintético (por porte) ou a planilha preenchida de uma empresa sem ERP
(`fontes/planilha.py`, a mesma lida pelo servidor MCP de Excel). Cada tool devolve
{"dados", "proveniencia"}; a allowlist por agente nega, fail-closed, o que o papel não tem
(NORM-02). Desde a revisão da DSM3, quem chama prova a identidade com a credencial que o
barramento emitiu no registro (`Agent.ferramenta`): declarar o nome de outro agente não basta.
Empresa sem ERP não tem `erp.realizado_por_conta`: a tool falha explicitamente e
o agente segue com a planilha. Toda chamada é auditada.

DSM3 — efeito externo protegido (CP7, REQ-S01): todas as tools são de leitura, exceto
`erp.corrigir` (estornar, reaprovar ou reclassificar um lançamento). Ela só existe na
allowlist do Orquestrador e só executa com o id de uma aprovação PROT-APR que o SVC-POL
confirme para aquela correção (`autorizar_efeito`); sem isso, nada chega à fonte de dados.
"""
from fin_mas.cognicao.perfis import perfil_cognitivo
from fin_mas.conhecimento import base as conhecimento
from fin_mas.env.dataset import BASE_DIRECIONADOR, RATEIO, VERSAO_RATEIO, Ambiente, Dataset
from fin_mas.services.politica import AprovacaoNecessaria

ALLOWLIST = {
    # DSM4 (ADR-010): as tools acrescentadas a AG-CUS, AG-RES, AG-CIN e AG-REL são de leitura e só são chamadas
    # pelas variantes BDI (níveis `local` e `llm`); no nível `basico` ninguém as usa.
    "AG-CUS": {"erp.balancete", "erp.direcionadores", "normas.cognicao"},
    "AG-ORC": {"planilhas.orcamento", "erp.realizado_por_conta", "normas.perfil",
               "planilhas.observacoes", "erp.historico"},  # percepções da cognição (ADR-008); só leitura
    "AG-RES": {"erp.balancete", "erp.historico_resultado", "normas.cognicao"},
    "AG-CIN": {"erp.lancamentos", "normas.alcadas", "normas.regras", "normas.perfil", "normas.buscar"},
    "AG-REL": {"normas.cognicao", "normas.buscar"},
    "AG-ORQ": {"erp.corrigir"},  # único efeito externo: exige aprovação (PROT-APR)
}
EFEITO_EXTERNO = {"erp.corrigir"}
COM_ARGUMENTOS = {"normas.buscar"}  # tools de leitura que recebem parâmetros além da competência
SO_COM_ERP = {"erp.realizado_por_conta", "erp.historico", "erp.historico_resultado"}  # sem ERP: falha explícita
ABA = {"erp.balancete": "Produtos+CustosFixos", "erp.lancamentos": "Lancamentos", "planilhas.orcamento": "Orcamento",
       "erp.realizado_por_conta": "Orcamento", "erp.corrigir": "Lancamentos", "planilhas.observacoes": "Orcamento",
       "erp.direcionadores": "CustosFixos"}
INDISPONIVEL = {"erp.historico": "empresa sem ERP: não há histórico mensal disponível",
                "erp.historico_resultado": "empresa sem ERP: não há histórico de resultado disponível"}


class ToolDenied(PermissionError):
    """Tool fora da allowlist do papel solicitante."""


class ToolIndisponivel(LookupError):
    """A fonte da empresa não oferece esta tool (ex.: empresa sem ERP)."""


class MCPGateway:
    def __init__(self, ambiente: Ambiente | Dataset, audit, bus, politica=None):
        self.ambiente = Ambiente.de_dataset(ambiente) if isinstance(ambiente, Dataset) else ambiente
        self.audit = audit
        self.bus = bus
        self.politica = politica  # SVC-POL: sem política, nenhum efeito externo é executado

    @property
    def ds(self) -> Dataset:
        return self.ambiente.dataset()

    def call(self, agente: str, tool: str, conversation_id: str, competencia: str | None = None,
             credencial: str | None = None, **args):
        """Executa a tool para `agente`, que precisa provar a identidade com a credencial do barramento."""
        if not self.bus.autenticar(agente, credencial):
            self.audit.record(self.bus.now, "mcp_denied", conversation_id=conversation_id, agente=agente, tool=tool,
                              motivo="identidade não autenticada (credencial ausente ou inválida)")
            raise ToolDenied(f"{agente}: identidade não autenticada para {tool}")
        if tool not in ALLOWLIST.get(agente, set()):
            self.audit.record(self.bus.now, "mcp_denied", conversation_id=conversation_id, agente=agente, tool=tool)
            raise ToolDenied(f"{agente} não pode chamar {tool}")
        ds = self.ambiente.dataset(competencia)
        consulta = {"entidade": ds.entidade, "competencia": ds.competencia, **args}
        if tool in SO_COM_ERP and not ds.perfil["tem_erp"]:
            self.audit.record(self.bus.now, "mcp_denied", conversation_id=conversation_id, agente=agente, tool=tool,
                              motivo="empresa sem ERP")
            raise ToolIndisponivel(INDISPONIVEL.get(tool, "empresa sem ERP: o realizado vem só da planilha"))
        if tool in EFEITO_EXTERNO:
            dados = self._efeito(agente, tool, conversation_id, ds, consulta, **args)
        elif tool in COM_ARGUMENTOS:
            dados = getattr(self, "_" + tool.replace(".", "_"))(ds, **args)
        else:
            dados = getattr(self, "_" + tool.replace(".", "_"))(ds)
        proveniencia = {"fonte": self._fonte(ds, tool), "consulta": consulta, "seed": ds.seed}
        self.audit.record(self.bus.now, "mcp_call", conversation_id=conversation_id, agente=agente, tool=tool,
                          consulta=consulta, fonte=proveniencia["fonte"])
        return {"dados": dados, "proveniencia": proveniencia}

    def _efeito(self, agente, tool, conversation_id, ds, consulta, aprovacao=None, lancamento=None, acao=None):
        try:
            if self.politica is None:
                raise AprovacaoNecessaria("sem SVC-POL configurado: efeito externo bloqueado")
            self.politica.autorizar_efeito(aprovacao, agente, lancamento, acao)
        except AprovacaoNecessaria as erro:
            self.audit.record(self.bus.now, "mcp_denied", conversation_id=conversation_id, agente=agente, tool=tool,
                              consulta=consulta, motivo=f"sem aprovação válida: {erro}")
            raise
        registro = ds.corrigir(lancamento, acao)
        self.politica.registrar_execucao(aprovacao, registro)
        return registro

    @staticmethod
    def _fonte(ds, tool) -> str:
        if hasattr(ds, "proveniencia") and tool in ABA:  # planilha real de empresa sem ERP
            return ds.proveniencia(ABA[tool])
        if tool.startswith("erp.") and not ds.perfil["tem_erp"]:
            return f"mcp://excel/{ABA[tool]}"  # empresa sintética sem ERP: dados vêm de planilhas
        return f"mcp://{tool.replace('.', '/')}"

    def _erp_balancete(self, ds):
        return {
            "produtos": [dict(p) for p in ds.produtos],
            "custos_fixos": [dict(c) for c in ds.custos_fixos],
        }

    def _erp_lancamentos(self, ds):
        return [dict(lanc) for lanc in ds.lancamentos]

    def _planilhas_orcamento(self, ds):
        return {
            "meses_decorridos": ds.gold["meses_decorridos"],
            "contas": [dict(c) for c in ds.orcamento],
        }

    def _normas_alcadas(self, ds):
        p = ds.perfil
        return {"limites": dict(p["limites_alcada"]), "cargos": dict(p["pessoas"]),  # None = sem limite
                "aprovadores": list(p["aprovadores"])}

    def _normas_regras(self, ds):
        return {"severidade": dict(ds.perfil["severidade"]), "versao": ds.perfil["versao"],
                "controle_compensatorio": dict(ds.perfil["controle_compensatorio"])}

    def _normas_perfil(self, ds):
        p = ds.perfil
        return {k: p[k] for k in ("porte", "titulo", "norma_contabil", "tem_erp", "fonte_primaria", "limiar_desvio",
                                  "pesos_cin", "pesos_orc", "max_ciclos_correcao", "versao")}

    def _planilhas_observacoes(self, ds):
        """Texto livre por conta (coluna "Observações"); planilha sem a coluna devolve vazio."""
        return {"observacoes": dict(getattr(ds, "observacoes", None) or {})}

    def _erp_historico(self, ds):
        historico = getattr(ds, "historico", None)
        return {"historico": historico() if callable(historico) else {}}

    # ---- DSM4 (ADR-010 e CP8): percepções das variantes BDI e base normativa; todas de leitura ----------
    def _erp_direcionadores(self, ds):
        """Direcionadores de rateio do período. Fonte sem a tabela (planilha real) devolve o rateio vigente."""
        fn = getattr(ds, "direcionadores", None)
        return fn() if callable(fn) else {"base": BASE_DIRECIONADOR, "versao": VERSAO_RATEIO, "valores": dict(RATEIO)}

    def _erp_historico_resultado(self, ds):
        fn = getattr(ds, "historico_resultado", None)
        return {"meses": fn() if callable(fn) else []}

    def _normas_cognicao(self, ds):
        """Perfil cognitivo do porte (models/cognicao.yaml): pesos dos desejos, público, compromisso e limiares."""
        return {**perfil_cognitivo(ds.perfil["porte"]), "tem_erp": ds.perfil["tem_erp"]}

    def _normas_buscar(self, ds, consulta: str = "", k: int = 3):
        """Trechos da base normativa que sustentam a consulta, com documento, trecho e versão (CP8).

        Sem evidência devolve `trechos` vazio: quem chama declara "sem evidência", nunca preenche.
        """
        if not isinstance(consulta, str) or not isinstance(k, int) or isinstance(k, bool):
            raise ValueError("normas.buscar: consulta (texto) e k (inteiro) são obrigatórios")
        return {"consulta": consulta, "versao": conhecimento.versao(), "trechos": conhecimento.buscar(consulta, min(k, 10))}

    def _erp_realizado_por_conta(self, ds):
        return {"meses_decorridos": ds.gold["meses_decorridos"], "realizado": dict(ds.realizado_erp)}
