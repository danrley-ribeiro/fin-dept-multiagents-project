"""Conector do ERP simulado: o dataset sintético de sempre, por seed e porte, com gabarito.

É o caso de referência: `Ambiente.de_conector(ConectorSimulado(42))` monta exatamente o mesmo
ambiente que `Ambiente(42)` (mesmo trace, byte a byte), porque `dataset()` entrega o próprio
`Dataset` sintético. `ler()` devolve a mesma competência no modelo canônico, que é o que o ERP
de demonstração (`erp_demo.py`) serve por HTTP num formato diferente.
"""
from fin_mas.conectores.base import Conector, DadosCanonicos, diagnostico, etapa
from fin_mas.env.dataset import COMPETENCIA, Ambiente
from fin_mas.env.empresa import EMPRESA, PESSOAS
from fin_mas.env.portes import PORTE_PADRAO


def canonico_do_dataset(ds) -> dict:
    """Registros canônicos (centavos, AAAA-MM) de um Dataset sintético; base do ERP de demonstração."""
    obs = getattr(ds, "observacoes", {}) or {}
    historico = ds.historico() if callable(getattr(ds, "historico", None)) else {}
    return {
        "Pessoas": [{"usuario": u, "nome": PESSOAS.get(u, (u,))[0], "cargo": c} for u, c in ds.perfil["pessoas"].items()],
        "Produtos": [{**p, "nome": None} for p in ds.produtos],
        "CustosFixos": [{**c, "descricao": None} for c in ds.custos_fixos],
        "Orcamento": [{**o, "observacao": obs.get(o["conta"])} for o in ds.orcamento],
        "Lancamentos": [{**x, "situacao": "ativo"} for x in ds.lancamentos],
        "Realizado": [{"conta": c, "realizado_acumulado": v} for c, v in ds.realizado_erp.items()],
        "Historico": [{"conta": conta, **{k: h[k] for k in ("competencia", "orcado", "realizado")}}
                      for conta, serie in historico.items() for h in serie],
    }


class ConectorSimulado(Conector):
    tipo = "erp_simulado"

    def __init__(self, seed: int = 42, porte: str = PORTE_PADRAO, plantar=(), agenda: dict | None = None,
                 id: str = "erp-simulado"):
        super().__init__(id, porte)
        self.ambiente = Ambiente(seed, plantar=plantar, agenda=agenda, porte=porte)

    def capacidades(self) -> set:
        return {"leitura", "escrita", "competencias", "gabarito"}

    def competencia_padrao(self) -> str:
        return self.ambiente.principal

    def testar(self) -> dict:
        ds = self.ambiente.dataset()
        return diagnostico([etapa("dados sintéticos", True, f"seed {self.ambiente.seed}, porte {ds.porte}, "
                                                            f"competência {ds.competencia}, {len(ds.lancamentos)} lançamentos")])

    def dataset(self, competencia):
        return self.ambiente.dataset(competencia)

    def ler(self, competencia) -> DadosCanonicos:
        ds = self.ambiente.dataset(competencia)
        dados = canonico_do_dataset(ds)
        return DadosCanonicos(ds.competencia, {"razao_social": EMPRESA["razao_social"], "sigla": ds.entidade,
                                               "porte": ds.porte, "tem_erp": ds.perfil["tem_erp"]},
                              dados, {aba: f"conector://{self.id}/{aba}" for aba in dados})

    def corrigir(self, competencia, lancamento, acao) -> dict:
        return self.ambiente.dataset(competencia).corrigir(lancamento, acao)

    def descricao(self) -> dict:
        return {**super().descricao(), "seed": self.ambiente.seed, "porte": self.ambiente.porte,
                "competencia": self.ambiente.principal if self.ambiente.agenda else COMPETENCIA}
