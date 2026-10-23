"""Ambiente sintético: dados do ERP/planilhas gerados por seed, com gabarito.

Valores monetários são inteiros em centavos (a tolerância de R$ 0,01 da DSM1
vira igualdade exata). O gabarito (`gold`) vem do que foi plantado, não de uma
reimplementação das regras dos agentes.
"""
import random
from dataclasses import dataclass, field

ENTIDADE = "EMP-01"
COMPETENCIA = "2026-09"
VERSAO_RATEIO = "rateio-v1"
RATEIO = {"UN-A": 60, "UN-B": 40}  # percentual por unidade de negócio
LIMIAR_PERCENTUAL = 10  # %
LIMIAR_ABSOLUTO = 5_000_00  # R$ 5.000,00 em centavos
USUARIOS = {  # cargo de cada usuário que cria ou aprova lançamentos
    "ana": "analista", "bruno": "analista", "carla": "gerente", "diego": "gerente", "elisa": "diretor",
}
LIMITES_ALCADA = {"analista": 10_000_00, "gerente": 50_000_00, "diretor": 200_000_00}
SEVERIDADE = {"alcada": "critica", "sod": "critica", "duplicidade": "critica", "competencia": "nao_critica"}
PLANTIOS = {"alcada", "sod", "duplicidade", "competencia", "desvio_orcamentario"}


def brl(centavos: int) -> str:
    sinal = "-" if centavos < 0 else ""
    reais, cents = divmod(abs(centavos), 100)
    return f"{sinal}R$ {reais:,}".replace(",", ".") + f",{cents:02d}"


def mes_no_trimestre(competencia: str) -> int:
    return (int(competencia[5:7]) - 1) % 3 + 1


def ratear(valor: int, rateio: dict) -> dict:
    """Divide em inteiros; o resto vai à última unidade para a soma fechar."""
    unidades = list(rateio)
    partes = {u: valor * rateio[u] // 100 for u in unidades}
    partes[unidades[-1]] += valor - sum(partes.values())
    return partes


@dataclass
class Dataset:
    seed: int
    entidade: str = ENTIDADE
    competencia: str = COMPETENCIA
    plantar: tuple = ()
    produtos: list = field(default_factory=list)
    custos_fixos: list = field(default_factory=list)
    orcamento: list = field(default_factory=list)
    lancamentos: list = field(default_factory=list)
    gold: dict = field(default_factory=dict)

    def __post_init__(self):
        desconhecidos = set(self.plantar) - PLANTIOS
        if desconhecidos:
            raise ValueError(f"plantios desconhecidos: {sorted(desconhecidos)}")
        rng = random.Random(self.seed)
        self._gerar_custos(rng)
        self._gerar_orcamento(rng)
        self._gerar_lancamentos(rng)

    # ---- custos e receita -------------------------------------------------
    def _gerar_custos(self, rng):
        for i, un in enumerate(["UN-A", "UN-A", "UN-B", "UN-B"], start=1):
            preco = rng.randint(80_00, 200_00)
            self.produtos.append({
                "id": f"P-{i}", "un": un, "qtd": rng.randint(100, 400), "preco": preco,
                "custo_variavel_unit": int(preco * rng.uniform(0.40, 0.65)),
            })
        for cc in ("CC-ADM", "CC-COM", "CC-OPS"):
            self.custos_fixos.append({"centro": cc, "valor": rng.randint(5_000_00, 15_000_00)})
        margens = {}
        for p in self.produtos:
            receita, cv = p["preco"] * p["qtd"], p["custo_variavel_unit"] * p["qtd"]
            margens[p["id"]] = {"receita": receita, "custo_variavel": cv, "margem": receita - cv}
        fixo_total = sum(c["valor"] for c in self.custos_fixos)
        fixo_un = ratear(fixo_total, RATEIO)
        por_un = {}
        for un in RATEIO:
            ids = [p["id"] for p in self.produtos if p["un"] == un]
            margem = sum(margens[i]["margem"] for i in ids)
            por_un[un] = {"margem": margem, "custo_fixo_rateado": fixo_un[un], "resultado": margem - fixo_un[un]}
        receita = sum(m["receita"] for m in margens.values())
        cv = sum(m["custo_variavel"] for m in margens.values())
        self.gold["margens_produto"] = margens
        self.gold["resultado_un"] = por_un
        self.gold["dre"] = {
            "receita": receita, "custos_variaveis": cv, "margem_contribuicao": receita - cv,
            "custos_fixos": fixo_total, "ebitda": receita - cv - fixo_total,
        }

    # ---- orçamento --------------------------------------------------------
    def _gerar_orcamento(self, rng):
        idx = mes_no_trimestre(self.competencia)
        contas = ["C-3001 Pessoal", "C-3002 Marketing", "C-3003 Servicos", "C-3004 Logistica"]
        for conta in contas:
            orcado_tri = rng.randint(30_000_00, 90_000_00) // 3 * 3
            acum = orcado_tri * idx // 3
            self.orcamento.append({
                "conta": conta, "orcado_trimestre": orcado_tri, "orcado_acumulado": acum,
                "realizado_acumulado": int(acum * rng.uniform(0.97, 1.03)),
            })
        # chamariz: +12% sobre base pequena, abaixo do limiar absoluto (não deve ser sinalizado)
        self.orcamento.append({
            "conta": "C-3005 Eventos", "orcado_trimestre": 30_000_00 // 3 * 3,
            "orcado_acumulado": 30_000_00 // 3 * 3 * idx // 3,
            "realizado_acumulado": 30_000_00 // 3 * 3 * idx // 3 * 112 // 100,
        })
        plantados = []
        if "desvio_orcamentario" in self.plantar:
            for linha in self.orcamento[:2]:
                linha["realizado_acumulado"] = linha["orcado_acumulado"] * 125 // 100
                plantados.append(linha["conta"])
        self.gold["desvios"] = sorted(plantados)
        self.gold["meses_decorridos"] = idx

    # ---- lançamentos e inconformidades -------------------------------------
    def _gerar_lancamentos(self, rng):
        nomes = list(USUARIOS)
        for n in range(1, 13):
            criador = rng.choice(nomes)
            aprovador = rng.choice([u for u in nomes if u != criador and USUARIOS[u] != "analista"])
            limite = LIMITES_ALCADA[USUARIOS[aprovador]]
            self.lancamentos.append({
                "id": f"L-{n:03d}", "fornecedor": f"F-{rng.randint(10, 99)}", "documento": f"NF-{1000 + n}",
                "valor": rng.randint(1_000_00, min(limite, 9_000_00)), "criador": criador,
                "aprovador": aprovador, "competencia": self.competencia,
            })
        nc = []
        proximo = len(self.lancamentos) + 1

        def novo(base, **mudancas):
            nonlocal proximo
            lanc = {**base, "id": f"L-{proximo:03d}", **mudancas}
            proximo += 1
            self.lancamentos.append(lanc)
            return lanc

        base = self.lancamentos[0]
        if "alcada" in self.plantar:
            lanc = novo(base, documento="NF-2001", aprovador="ana", criador="bruno", valor=15_000_00)
            nc.append({"regra": "alcada", "lancamento": lanc["id"], "severidade": SEVERIDADE["alcada"]})
        if "sod" in self.plantar:
            lanc = novo(base, documento="NF-2002", criador="carla", aprovador="carla", valor=4_000_00)
            nc.append({"regra": "sod", "lancamento": lanc["id"], "severidade": SEVERIDADE["sod"]})
        if "duplicidade" in self.plantar:
            lanc = novo(base)  # mesmo fornecedor, documento e valor do primeiro lançamento
            nc.append({"regra": "duplicidade", "lancamento": lanc["id"], "severidade": SEVERIDADE["duplicidade"]})
        if "competencia" in self.plantar:
            lanc = novo(base, documento="NF-2003", competencia="2026-08", valor=2_000_00)
            nc.append({"regra": "competencia", "lancamento": lanc["id"], "severidade": SEVERIDADE["competencia"]})
        self.gold["nao_conformidades"] = sorted(nc, key=lambda x: (x["regra"], x["lancamento"]))
