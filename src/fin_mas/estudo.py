"""Experimento redesenhado da DSM4 (pré-registro em docs/dsm4/experimento.md).

    python -m fin_mas experimento --replicas 30 --out docs/dsm4/resultados
    python -m fin_mas experimento --rapido --out /tmp/experimento      # confere o aparato em segundos

Quatro braços (SMA básico, SMA com cognição local, workflow centralizado equivalente e workflow
mínimo da DSM3) sob as mesmas seeds, em quatro blocos:

- A  principal: braços x condições de falha x portes x intenções;
- B  varredura: um parâmetro de coordenação por vez, no porte médio;
- C  ablação: um mecanismo desligado por vez, com pedido concorrente e desvio irregular plantado;
- D  controle de acesso: o SMA com decisão por pessoa (SVC-IAM), com e sem ataque.

Cada execução vira uma linha de `execucoes.csv`, gravada antes de qualquer agregação. A análise
(`analisar`) trabalha só sobre essas linhas: agrega por seed, descreve com IC por bootstrap e
aplica os testes do plano de análise. `experimentos.py` (DSM3) fica como está.
"""
import csv
import hashlib
import json
import re
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from fin_mas import __version__, baseline, baseline_eq, caos, estatistica, invariantes, metricas
from fin_mas.caos import ModeloFalhas
from fin_mas.env.dataset import Dataset
from fin_mas.env.portes import PORTES, versao_normas
from fin_mas.env.scenarios import Scenario, run_scenario
from fin_mas.parametros import PADRAO, Parametros

ALFA = 0.05
BRACOS = ("sma_basico", "sma_local", "wf_equivalente", "wf_minimo")
ROTULOS = {"sma_basico": "SMA básico", "sma_local": "SMA com cognição local",
           "wf_equivalente": "workflow equivalente", "wf_minimo": "workflow mínimo (DSM3)"}
INTENCOES = ("fechar_mes", "avaliar_orcamento")
_COMBINADAS = {"perda": 0.10, "jitter": 2, "indisponibilidades": 1, "aprovador": "lento"}
CONDICOES = {
    "nominal": {},
    "perda_baixa": {"perda": 0.05},
    "perda_media": {"perda": 0.15},
    "perda_alta": {"perda": 0.30},
    "indisponibilidade": {"indisponibilidades": 1},
    "humano_lento": {"aprovador": "lento"},
    "combinadas": dict(_COMBINADAS),
    "combinadas_ataque": {**_COMBINADAS, "ataque": True},
    "consulta_instavel": {"perda_enlaces": (("AG-CIN", "query-ref", 0.5),)},  # só no bloco C
}
CONDICOES_A = ("nominal", "perda_baixa", "perda_media", "perda_alta", "indisponibilidade", "humano_lento",
               "combinadas", "combinadas_ataque")
FALHAS_DE_COMUNICACAO = ("perda_baixa", "perda_media", "perda_alta", "indisponibilidade", "combinadas")
PERDAS = ("perda_baixa", "perda_media", "perda_alta")
VARREDURA = {"prazo_subtarefa": (15, 30, 60), "max_tentativas": (1, 2, 3), "max_correcoes": (0, 2),
             "ttl_reserva": (40, 80, 200), "prazo_aprovacao": (10, 20, 40), "limiar_percentual": (5, 10, 20)}
PADRAO_VARREDURA = {"prazo_subtarefa": 30, "max_tentativas": 2, "max_correcoes": 2, "ttl_reserva": 200,
                    "prazo_aprovacao": 20, "limiar_percentual": 10}
VALE_PARA_O_WORKFLOW = ("max_correcoes", "prazo_aprovacao", "limiar_percentual")
ABLACAO = {  # variante -> (parâmetros, cognição)
    "completo": ({}, "local"),
    "sem_reenvio": ({"max_tentativas": 1}, "local"),
    "sem_reserva": ({"reserva_periodo": False}, "local"),
    "sem_correcao": ({"max_correcoes": 0}, "local"),
    "sem_negociacao": ({"max_extensao": 0}, "local"),
    "sem_cognicao_local": ({}, "basico"),
}
CONDICOES_C = ("nominal", "perda_media", "consulta_instavel")
CONDICOES_D = ("nominal", "combinadas_ataque")
CHAVE = ("bloco", "braco", "condicao", "porte", "intencao", "seed", "variante")
CAMPOS = [*CHAVE, "plantios", "perfil_aprovador", "status", "concluida", "resposta_explicita",
          "classificacao_correta", "sinalizacao_correta", "falsos_desvios", "desvios_omitidos", "conformidade_correta", "dre_correta",
          "criticas_publicadas_sem_tratamento", "criticas_corrigidas", "resultado_igual_ao_nominal",
          "execucao_correta", "degradacao_segura", "mensagens", "mensagens_coordenacao", "latencia_ticks",
          "decisoes", "distribuicao_decisoria", "reconsideracoes", "intervencoes_humanas", "aprovacoes_expiradas",
          "mensagens_rejeitadas", "perdas", "prazos_esgotados", "reenvios", "t_primeira_falha", "recuperacao_ticks",
          "ataques_tentados", "ataques_aceitos", "ataques_sem_premissa", "violacoes_invariantes", "invariantes_violados",
          "inv03_aviso_sem_transicao", "registros_trace", "hipoteses_confirmadas", "hipoteses_refutadas",
          "hipoteses_arquivadas", "consultas_de_verificacao", "negociacoes_de_prazo", "publicacoes_do_periodo",
          "efeitos_falhos", "sinalizadas", "atribuidas", "correcoes", "ebitda", "erro", "hash"]
SEM_AVALIACAO = "n/d"  # a avaliação orçamentária não chegou a ser produzida
AVISO_SEM_TRANSICAO = re.compile(r"^INV-03: transição (\S+) --timeout--> \1 ")


@dataclass(frozen=True)
class Celula:
    bloco: str
    braco: str
    condicao: str
    porte: str
    intencao: str
    seed: int
    variante: str = "padrao"
    parametros: Parametros = PADRAO
    cognicao: str | None = None  # None = a do braço
    forcar: tuple = ()  # plantios sempre presentes (bloco C)
    concorrente: bool = False  # segundo pedido de fechamento do mesmo mês, 2 ticks depois (bloco C)
    acesso: bool = False  # SVC-IAM ligado: a decisão leva o atestado de uma pessoa (bloco D)

    @property
    def chave(self) -> tuple:
        return tuple(getattr(self, k) for k in CHAVE)


# ---- desenho -----------------------------------------------------------------------------------
def plano(replicas: int = 30, rapido: bool = False) -> list[Celula]:
    """Todas as execuções do experimento, em ordem fixa. `rapido` reduz tudo para conferir o aparato."""
    seeds = range(1, (min(replicas, 3) if rapido else replicas) + 1)
    portes = ("micro", "media") if rapido else PORTES
    cond_a = ("nominal", "perda_media", "combinadas", "combinadas_ataque") if rapido else CONDICOES_A
    varredura = {k: v for k, v in VARREDURA.items() if not rapido or k in ("max_tentativas", "max_correcoes")}
    cond_c = ("nominal", "consulta_instavel") if rapido else CONDICOES_C
    celulas = []
    for condicao in cond_a:
        for braco in BRACOS[:3] + (BRACOS[3:] if condicao == "nominal" else ()):
            celulas += [Celula("A", braco, condicao, porte, intencao, seed)
                        for porte in portes for intencao in INTENCOES for seed in seeds]
    variantes = [("padrao", PADRAO, True)]
    for parametro, niveis in varredura.items():
        variantes += [(f"{parametro}={v}", replace(PADRAO, **{parametro: v}), parametro in VALE_PARA_O_WORKFLOW)
                      for v in niveis if v != PADRAO_VARREDURA[parametro]]
    for condicao in ("nominal", "combinadas"):
        for variante, parametros, no_workflow in variantes:
            for braco in ("sma_basico",) + (("wf_equivalente",) if no_workflow else ()):
                celulas += [Celula("B", braco, condicao, "media", intencao, seed, variante, parametros)
                            for intencao in INTENCOES for seed in seeds]
    for condicao in cond_c:
        for variante, (mudancas, cognicao) in ABLACAO.items():
            celulas += [Celula("C", "sma_local" if cognicao == "local" else "sma_basico", condicao, "media", intencao,
                               seed, variante, replace(PADRAO, **mudancas), cognicao, ("desvio_irregular",), True)
                        for intencao in INTENCOES for seed in seeds]
    for condicao in CONDICOES_D:
        celulas += [Celula("D", "sma_basico", condicao, "media", intencao, seed, "acesso", acesso=True)
                    for intencao in INTENCOES for seed in seeds]
    return celulas


def modelo_de(c: Celula) -> ModeloFalhas:
    config = CONDICOES[c.condicao]
    return ModeloFalhas(c.seed, **config, plantios_forcados=c.forcar, persona="controller" if c.acesso else None,
                        ataque_acesso=c.acesso and bool(config.get("ataque")))


# ---- execução e medição ------------------------------------------------------------------------
@contextmanager
def protocolos_em_cache():
    """Lê `models/protocols.yaml` uma vez por experimento, em vez de duas por execução.

    Os protocolos são imutáveis; a leitura do YAML é a maior parte do tempo de montar um sistema.
    Só o tempo de parede muda: os traces são os mesmos.
    """
    from fin_mas.core import bus, fsm
    from fin_mas.services import locks
    original, protocolos = fsm.load_protocols, fsm.load_protocols()

    def carregar(path=None):
        return protocolos if path is None else original(path)

    bus.load_protocols = locks.load_protocols = carregar
    try:
        yield
    finally:
        bus.load_protocols = locks.load_protocols = original


def executar_celula(c: Celula) -> tuple[dict, float]:
    """Roda uma execução e devolve (linha de métricas, milissegundos de parede)."""
    modelo = modelo_de(c)
    plantios = modelo.plantios()
    linha = {**dict(zip(CHAVE, c.chave)), "plantios": "|".join(plantios), "perfil_aprovador": modelo.perfil_aprovador()}
    inicio = time.perf_counter()
    try:
        if c.braco.startswith("sma"):
            pedidos = ((c.intencao, None, 1), ("fechar_mes", None, 3)) if c.concorrente and c.intencao == "fechar_mes" else ()
            sc = Scenario("estudo", f"experimento da DSM4, bloco {c.bloco}", c.intencao, plantar=plantios,
                          porte=c.porte, pedidos=pedidos, acesso=c.acesso, solicitante="elisa" if c.acesso else None,
                          cognicao=c.cognicao or ("local" if c.braco == "sma_local" else "basico"))
            execucao = run_scenario(sc, seed=c.seed, parametros=c.parametros, caos=modelo)
            ms = (time.perf_counter() - inicio) * 1000
            linha.update(medir_sma(execucao))
        elif c.braco == "wf_equivalente":
            w = baseline_eq.executar(c.seed, plantios, c.intencao, c.porte, parametros=c.parametros, caos=modelo)
            ms = (time.perf_counter() - inicio) * 1000
            linha.update(medir_workflow(w))
        else:
            ds = Dataset(seed=c.seed, plantar=plantios, porte=c.porte)
            c.parametros.aplicar_limiares(ds)
            res = baseline.executar(ds, c.intencao)
            ms = (time.perf_counter() - inicio) * 1000
            linha.update(medir_minimo(res, ds))
    except Exception as erro:  # nenhuma execução é descartada: o erro vira uma linha
        ms = (time.perf_counter() - inicio) * 1000
        linha.update(status="erro", concluida=0, resposta_explicita=0, erro=f"{type(erro).__name__}: {erro}"[:200])
    return linha, ms


def _lista(valores) -> str:
    return "|".join(valores)


def _classificacao(sinalizadas, atribuidas, gold) -> dict:
    if sinalizadas is None:
        return {"classificacao_correta": None, "sinalizacao_correta": None, "falsos_desvios": None, "desvios_omitidos": None,
                "sinalizadas": SEM_AVALIACAO, "atribuidas": SEM_AVALIACAO}
    sinalizadas, atribuidas = sorted(sinalizadas), sorted(atribuidas or [])
    # `sinalizacao_correta` (só as contas sinalizadas, a definição da DSM3) não está no pré-registro: é exploratória
    return {"classificacao_correta": int(sinalizadas == gold["desvios"] and atribuidas == gold["desvios_atribuidos"]),
            "sinalizacao_correta": int(sinalizadas == gold["desvios"]),
            "falsos_desvios": len(set(sinalizadas) - set(gold["desvios"])),
            "desvios_omitidos": len(set(gold["desvios"]) - set(sinalizadas)),
            "sinalizadas": _lista(sinalizadas), "atribuidas": _lista(atribuidas)}


def _conformidade(achados, gold) -> int | None:
    if achados is None:
        return None
    return int(sorted((a["regra"], a["lancamento"], a["severidade"]) for a in achados)
               == sorted((a["regra"], a["lancamento"], a["severidade"]) for a in gold["nao_conformidades"]))


def _falhas(registros, fim) -> dict:
    perdas = [r["t"] for r in registros if r["kind"] == "drop"]
    prazos = [r["t"] for r in registros if r["kind"] == "timeout"]
    primeira = min(perdas + prazos) if perdas or prazos else None
    return {"perdas": len(perdas), "prazos_esgotados": len(prazos), "t_primeira_falha": primeira,
            "recuperacao_ticks": None if primeira is None or fim is None else fim - primeira}


def violacoes(registros) -> tuple[list[str], int]:
    """(invariantes violados, avisos de prazo que o INV-03 da v0.5.0 acusa sem haver transição).

    No PROT-CMP o barramento avisa o Orquestrador do prazo esgotado sem mudar o estado (`de` = `para`).
    Não é uma transição; o verificador da v0.5.0 a contava como violação do INV-03. Aqui ela é
    contada à parte, para o resultado não depender dessa correção do verificador.
    """
    todas = invariantes.verificar(registros)
    avisos = [v for v in todas if AVISO_SEM_TRANSICAO.match(v)]
    return [v.split(":")[0] for v in todas if v not in avisos], len(avisos)


ATAQUE_DO_ENVOLVIDO = "aprovador que participou do lançamento vetado decide sobre ele (ana corrige)"


def _ataques(execucao) -> dict:
    """Ataques tentados e aceitos; à parte, os aceitos cuja premissa não vale nos dados sorteados.

    `env/ataques_acesso.py` foi escrito para um cenário em que a analista ana participou do
    lançamento vetado. Com plantios sorteados isso nem sempre é verdade: quando ela **não** está
    entre os envolvidos do ticket, a decisão dela é a de uma aprovadora autorizada, com atestado
    válido e sem conflito, e a política a aceita corretamente. Esses casos não são falha de
    controle e são contados em `ataques_sem_premissa`.
    """
    tentados = aceitos = sem_premissa = 0
    tickets = execucao.system.politica.tickets
    for r in execucao.audit.records:
        if r["kind"] != "ataques":
            continue
        for x in r["resultados"]:
            tentados += 1
            if x["aceito"]:
                aceitos += 1
                envolvidos = tickets.get(r.get("aprovacao"), {}).get("envolvidos", [])
                sem_premissa += int(x["ataque"] == ATAQUE_DO_ENVOLVIDO and "ana" not in envolvidos)
    return {"ataques_tentados": tentados, "ataques_aceitos": aceitos, "ataques_sem_premissa": sem_premissa}


def medir_sma(execucao) -> dict:
    """Métricas da primeira solicitação de uma execução do SMA, lidas do trace e do gabarito."""
    sid, audit, sistema = execucao.sid, execucao.audit, execucao.system
    base = metricas.medir(execucao, sid)
    ds, reg = sistema.dataset, audit.records
    familia = set(audit.familia(sid))
    da_familia = [r for r in reg if r.get("conversation_id") in familia]
    resposta = sistema.usuario.resposta(sid)
    orc = next((r["content"] for r in reversed(da_familia) if r["kind"] == "send" and r.get("sender") == "AG-ORC"
                and r["performative"] == "inform" and r.get("protocol") == "PROT-DEL"), None)
    parecer = next((r["content"] for r in da_familia if r["kind"] == "send" and r.get("protocol") == "PROT-CMP"
                    and r["performative"] in ("conforme", "nao_conforme_nao_critico", "veto")), None)
    inicio = next(r["t"] for r in da_familia if r["kind"] == "open" and r["conversation_id"] == sid)
    fim = None if base["latencia_ticks"] is None or resposta is None else inicio + base["latencia_ticks"]
    violados, avisos = violacoes(reg)
    cognicao = metricas.medir_cognicao(execucao)
    dre = resposta.content["resultado"].get("dre") if resposta is not None and resposta.performative == "inform" else None
    return {
        "status": base["status"], "concluida": base["concluida"], "resposta_explicita": base["resposta_explicita"],
        **_classificacao(orc["sinalizadas"] if orc else None, orc.get("atribuidas_a_controle") if orc else None, ds.gold),
        "conformidade_correta": _conformidade(parecer["achados"] if parecer else None, ds.gold),
        "dre_correta": base["dre_correta"],
        "criticas_publicadas_sem_tratamento": base["criticas_publicadas_sem_tratamento"],
        "criticas_corrigidas": base["criticas_corrigidas"],
        "mensagens": base["mensagens_a2a"],
        "mensagens_coordenacao": sum(1 for r in da_familia if r["kind"] in ("open", "send")
                                     and r.get("protocol") not in (None, "PROT-SOL")),
        "latencia_ticks": base["latencia_ticks"] if resposta is not None else None,
        **{k: base[k] for k in ("decisoes", "distribuicao_decisoria", "reconsideracoes", "intervencoes_humanas",
                                "aprovacoes_expiradas", "mensagens_rejeitadas")},
        **_falhas(da_familia, fim),
        "reenvios": sum(1 for r in da_familia if r["kind"] == "decision" and r.get("resultado") == "reenviar"),
        **_ataques(execucao),
        "violacoes_invariantes": len(violados), "invariantes_violados": _lista(sorted(set(violados))),
        "inv03_aviso_sem_transicao": avisos, "registros_trace": len(reg),
        "hipoteses_confirmadas": cognicao["confirmadas"], "hipoteses_refutadas": cognicao["refutadas"],
        "hipoteses_arquivadas": cognicao["arquivadas"], "consultas_de_verificacao": cognicao["consultas_de_verificacao"],
        "negociacoes_de_prazo": cognicao["negociacoes_de_prazo"],
        "publicacoes_do_periodo": sum(1 for r in reg if r["kind"] == "send" and r.get("protocol") == "PROT-SOL"
                                      and r["performative"] == "inform" and r["content"].get("intencao") == "fechar_mes"),
        "efeitos_falhos": sum(1 for r in reg if r["kind"] == "politica" and r.get("evento") == "efeito_falhou"),
        "correcoes": _lista(f"{c['lancamento']}:{c['acao']}" for c in ds.correcoes),
        "ebitda": dre["ebitda"] if dre else None, "hash": execucao.hash,
    }


def _criticas_sem_tratamento(gold, corrigidos, ressalvas) -> int:
    criticas = [n for n in gold["nao_conformidades"] if n["severidade"] == "critica"]
    return sum(1 for n in criticas if n["lancamento"] not in corrigidos
               and not any(x.startswith(f"waiver de {n['regra']} em {n['lancamento']}") for x in ressalvas))


def medir_workflow(w) -> dict:
    """As mesmas métricas para o workflow equivalente (o verificador de invariantes é do SMA e não se aplica)."""
    ds, reg, fechar = w.dataset, w.audit.records, w.intencao == "fechar_mes"
    corrigidos = {c["lancamento"] for c in ds.correcoes}
    criticas = [n for n in ds.gold["nao_conformidades"] if n["severidade"] == "critica"]
    mensagens = sum(1 for r in reg if r["kind"] in ("open", "send") and r.get("protocol"))
    return {
        "status": w.status, "concluida": int(w.publicado), "resposta_explicita": 1,
        **_classificacao(w.sinalizadas, w.atribuidas, ds.gold),
        "conformidade_correta": _conformidade(w.achados, ds.gold) if fechar else None,
        "dre_correta": int(w.dre == ds.gold["dre"]) if fechar and w.publicado else None,
        "criticas_publicadas_sem_tratamento": _criticas_sem_tratamento(ds.gold, corrigidos, w.ressalvas)
        if fechar and w.publicado else 0,
        "criticas_corrigidas": sum(1 for n in criticas if n["lancamento"] in corrigidos),
        "mensagens": mensagens, "mensagens_coordenacao": mensagens, "latencia_ticks": w.ticks,
        "decisoes": len(w.decisoes), "distribuicao_decisoria": 0.0, "reconsideracoes": 0,
        "intervencoes_humanas": sum(1 for r in reg if r["kind"] == "send" and r["performative"] in ("approve", "reject")),
        "aprovacoes_expiradas": sum(1 for r in reg if r["kind"] == "timeout"),
        "mensagens_rejeitadas": sum(1 for r in reg if r["kind"] == "rejected"),
        **_falhas(reg, w.ticks), "reenvios": 0, "registros_trace": len(reg),
        "publicacoes_do_periodo": int(fechar and w.publicado),
        "efeitos_falhos": sum(1 for r in reg if r["kind"] == "politica" and r.get("evento") == "efeito_falhou"),
        "correcoes": _lista(f"{c['lancamento']}:{c['acao']}" for c in w.correcoes),
        "ebitda": w.dre["ebitda"] if fechar and w.publicado else None, "hash": w.audit.digest(),
    }


def medir_minimo(res, ds) -> dict:
    """Workflow mínimo da DSM3: sem veto, sem correção, sem reconciliação e sem atribuição."""
    base = metricas.medir_baseline(res, ds)
    fechar = res.intencao == "fechar_mes"
    return {
        "status": base["status"], "concluida": 1, "resposta_explicita": 1,
        **_classificacao(res.sinalizadas, [], ds.gold),
        "conformidade_correta": _conformidade(res.achados, ds.gold) if fechar else None,
        "dre_correta": base["dre_correta"],
        "criticas_publicadas_sem_tratamento": base["criticas_publicadas_sem_tratamento"], "criticas_corrigidas": 0,
        "mensagens": 0, "mensagens_coordenacao": 0, "latencia_ticks": base["latencia_ticks"],
        "decisoes": base["decisoes"], "distribuicao_decisoria": 0.0, "reconsideracoes": 0, "intervencoes_humanas": 0,
        "aprovacoes_expiradas": 0, "mensagens_rejeitadas": 0, "perdas": 0, "prazos_esgotados": 0, "reenvios": 0,
        "registros_trace": 0, "publicacoes_do_periodo": int(fechar), "efeitos_falhos": 0, "correcoes": "",
        "ebitda": res.dre["ebitda"] if res.dre else None, "hash": "",
    }


def assinatura(linha) -> tuple:
    """O que precisa ser igual para dois resultados serem o mesmo: status, DRE, classificação e correções."""
    return (linha.get("status"), linha.get("ebitda"), linha.get("dre_correta"), linha.get("sinalizadas"),
            linha.get("atribuidas"), linha.get("correcoes"))


def marcar_robustez(linhas) -> None:
    """Compara cada execução com a nominal do mesmo braço, variante, porte, intenção e seed."""
    nominais = {(r["bloco"], r["braco"], r["porte"], r["intencao"], r["seed"], r["variante"]): r
                for r in linhas if r["condicao"] == "nominal"}
    for r in linhas:
        ref = nominais.get((r["bloco"], r["braco"], r["porte"], r["intencao"], r["seed"], r["variante"]))
        if ref is None:
            continue
        igual = int(assinatura(r) == assinatura(ref))
        seguro = bool(r.get("resposta_explicita")) and not r.get("criticas_publicadas_sem_tratamento")
        r["resultado_igual_ao_nominal"] = igual
        r["execucao_correta"] = int(seguro and igual)
        r["degradacao_segura"] = int(seguro and not igual)


def executar(celulas, progresso=None) -> tuple[list[dict], list[dict]]:
    """Roda o plano inteiro. Devolve (linhas de métricas, tempos de parede)."""
    linhas, tempos = [], []
    with protocolos_em_cache():
        for i, c in enumerate(celulas, start=1):
            linha, ms = executar_celula(c)
            linhas.append({k: linha.get(k) for k in CAMPOS})
            tempos.append({**dict(zip(CHAVE, c.chave)), "ms": f"{ms:.3f}"})
            if progresso and (i % 500 == 0 or i == len(celulas)):
                progresso(i, len(celulas))
    marcar_robustez(linhas)
    return linhas, tempos


# ---- análise -----------------------------------------------------------------------------------
def selecionar(linhas, **filtros) -> list[dict]:
    """Linhas que casam com os filtros; um valor em tupla ou conjunto aceita qualquer um deles."""
    def casa(r):
        return all(r[k] in v if isinstance(v, (tuple, set, frozenset, list)) else r[k] == v for k, v in filtros.items())
    return [r for r in linhas if casa(r)]


def por_seed(linhas, metrica) -> dict:
    """Unidade estatística: média da métrica nas células de cada seed (valores ausentes ficam de fora)."""
    soma: dict[int, list] = {}
    for r in linhas:
        if r.get(metrica) is not None:
            soma.setdefault(r["seed"], []).append(r[metrica])
    return {seed: sum(v) / len(v) for seed, v in sorted(soma.items())}


def descrever(linhas, metrica) -> dict:
    valores = list(por_seed(linhas, metrica).values())
    d = estatistica.descrever(valores)
    d["execucoes"] = sum(1 for r in linhas if r.get(metrica) is not None)
    return d


def comparar(familia, rotulo, metrica, a, b, nome_a, nome_b) -> dict:
    """Teste pareado por seed entre dois conjuntos de linhas (a - b)."""
    va, vb = por_seed(a, metrica), por_seed(b, metrica)
    seeds = [s for s in va if s in vb]
    x, y = [va[s] for s in seeds], [vb[s] for s in seeds]
    teste = {"familia": familia, "comparacao": rotulo, "metrica": metrica, "a": nome_a, "b": nome_b,
             "tipo": "Wilcoxon pareado", "n": len(seeds)}
    if not seeds:
        return {**teste, "p": None, "observacao": "sem pares"}
    r = estatistica.wilcoxon_pareado(x, y)
    diferencas = [p - q for p, q in zip(x, y)]
    inferior, superior = estatistica.ic_bootstrap(diferencas)
    delta = estatistica.cliff(x, y)
    return {**teste, "media_a": round(estatistica.media(x), 4), "media_b": round(estatistica.media(y), 4),
            "diferenca_media": round(estatistica.media(diferencas), 4), "ic95_diferenca": [round(inferior, 4), round(superior, 4)],
            "pares_diferentes": r["n_efetivo"], "estatistica": min(r["w_mais"], r["w_menos"]),
            "p": round(r["p"], 6), "metodo": r["metodo"], "cliff": round(delta, 4),
            "magnitude": estatistica.magnitude(delta)}


def comparar_grupos(familia, rotulo, metrica, a, b, nome_a, nome_b) -> dict:
    """Mann-Whitney entre execuções de dois grupos independentes."""
    x = [r[metrica] for r in a if r.get(metrica) is not None]
    y = [r[metrica] for r in b if r.get(metrica) is not None]
    teste = {"familia": familia, "comparacao": rotulo, "metrica": metrica, "a": nome_a, "b": nome_b,
             "tipo": "Mann-Whitney", "n": f"{len(x)} x {len(y)}"}
    if not x or not y:
        return {**teste, "p": None, "observacao": "grupo vazio"}
    r = estatistica.mann_whitney(x, y)
    delta = estatistica.cliff(x, y)
    return {**teste, "media_a": round(estatistica.media(x), 4), "media_b": round(estatistica.media(y), 4),
            "mediana_a": estatistica.mediana(x), "mediana_b": estatistica.mediana(y),
            "diferenca_media": round(estatistica.media(x) - estatistica.media(y), 4), "estatistica": min(r["u1"], r["u2"]),
            "p": round(r["p"], 6), "metodo": r["metodo"], "cliff": round(delta, 4),
            "magnitude": estatistica.magnitude(delta)}


def ajustar(testes) -> list[dict]:
    """Holm dentro de cada família.

    Ficam fora da correção as comparações sem pares e as idênticas em todos os pares: pelo plano de
    análise, sem nenhuma diferença o teste não se aplica (o resultado é relatado como identidade).
    """
    por_familia: dict[str, list] = {}
    for t in testes:
        if t.get("p") is not None and t.get("pares_diferentes") != 0:
            por_familia.setdefault(t["familia"], []).append(t)
        else:
            t["p_holm"], t["significativo"] = None, False
    for grupo in por_familia.values():
        for t, p in zip(grupo, estatistica.holm([t["p"] for t in grupo])):
            t["p_holm"], t["significativo"] = round(p, 6), p < ALFA
    return testes


def _pares_com_assinatura_diferente(a, b) -> dict:
    ref = {(r["porte"], r["intencao"], r["seed"]): r for r in b}
    pares = [(r, ref[(r["porte"], r["intencao"], r["seed"])]) for r in a if (r["porte"], r["intencao"], r["seed"]) in ref]
    diferentes = [f"{x['porte']}/{x['intencao']}/seed {x['seed']}" for x, y in pares if assinatura(x) != assinatura(y)]
    return {"pares": len(pares), "diferentes": len(diferentes), "quais": diferentes[:20]}


def analisar(linhas) -> dict:
    """Tabelas e testes do plano de análise, a partir só das linhas de `execucoes.csv`."""
    A = selecionar(linhas, bloco="A")
    condicoes = [c for c in CONDICOES_A if selecionar(A, condicao=c)]
    bracos = [b for b in BRACOS if selecionar(A, braco=b)]
    portes = [p for p in PORTES if selecionar(A, porte=p)]

    def a(**f):
        return selecionar(A, **f)

    tabelas, testes = {}, []
    # RQ1: qualidade na condição nominal
    qualidade = ("classificacao_correta", "sinalizacao_correta", "conformidade_correta", "dre_correta", "criticas_publicadas_sem_tratamento",
                 "concluida", "resposta_explicita")
    tabelas["rq1_qualidade_nominal"] = {b: {m: descrever(a(braco=b, condicao="nominal"), m) for m in qualidade}
                                        for b in bracos}
    identidade = {"sma_basico_x_wf_equivalente": _pares_com_assinatura_diferente(
        a(braco="sma_basico", condicao="nominal"), a(braco="wf_equivalente", condicao="nominal")),
        "sma_local_x_sma_basico": _pares_com_assinatura_diferente(
            a(braco="sma_local", condicao="nominal"), a(braco="sma_basico", condicao="nominal"))}
    for x, y in (("sma_basico", "wf_equivalente"), ("sma_basico", "wf_minimo"), ("wf_equivalente", "wf_minimo")):
        for m in ("classificacao_correta", "conformidade_correta", "criticas_publicadas_sem_tratamento"):
            testes.append(comparar("RQ1", f"{x} x {y}, nominal", m, a(braco=x, condicao="nominal"),
                                   a(braco=y, condicao="nominal"), x, y))
    # RQ2: robustez por condição
    robustez = ("execucao_correta", "degradacao_segura", "resposta_explicita", "concluida",
                "criticas_publicadas_sem_tratamento")
    tabelas["rq2_robustez"] = {c: {b: {m: descrever(a(braco=b, condicao=c), m) for m in robustez}
                                   for b in bracos[:3]} for c in condicoes if c != "nominal"}
    for c in condicoes:
        if c != "nominal":
            testes.append(comparar("RQ2", f"sma_basico x wf_equivalente, {c}", "execucao_correta",
                                   a(braco="sma_basico", condicao=c), a(braco="wf_equivalente", condicao=c),
                                   "sma_basico", "wf_equivalente"))
    for x, y in (("perda_baixa", "perda_media"), ("perda_media", "perda_alta")):
        if x in condicoes and y in condicoes:
            testes.append(comparar("RQ2", f"sma_basico, {x} x {y}", "execucao_correta",
                                   a(braco="sma_basico", condicao=x), a(braco="sma_basico", condicao=y), x, y))
    # RQ3: custo de coordenação e do controle de acesso
    custo = ("mensagens", "mensagens_coordenacao", "latencia_ticks", "decisoes", "intervencoes_humanas")
    tabelas["rq3_custo"] = {c: {b: {m: descrever(a(braco=b, condicao=c), m) for m in custo} for b in bracos
                                if a(braco=b, condicao=c)} for c in condicoes}
    for c in ("nominal", "combinadas"):
        for m in ("mensagens_coordenacao", "latencia_ticks"):
            testes.append(comparar("RQ3", f"sma_basico x wf_equivalente, {c}", m, a(braco="sma_basico", condicao=c),
                                   a(braco="wf_equivalente", condicao=c), "sma_basico", "wf_equivalente"))
    D = selecionar(linhas, bloco="D")
    sem_acesso = a(braco="sma_basico", porte="media")
    acesso = ("mensagens", "latencia_ticks", "registros_trace", "mensagens_rejeitadas", "execucao_correta",
              "ataques_tentados", "ataques_aceitos", "ataques_sem_premissa")
    tabelas["rq3_acesso"] = {c: {"com_acesso": {m: descrever(selecionar(D, condicao=c), m) for m in acesso},
                                 "sem_acesso": {m: descrever(selecionar(sem_acesso, condicao=c), m) for m in acesso}}
                             for c in CONDICOES_D if selecionar(D, condicao=c)}
    for m in ("mensagens", "latencia_ticks", "registros_trace"):
        testes.append(comparar("RQ3", "controle de acesso ligado x desligado, nominal, porte médio", m,
                               selecionar(D, condicao="nominal"), selecionar(sem_acesso, condicao="nominal"),
                               "com_acesso", "sem_acesso"))
    # RQ4: recuperação das execuções do SMA atingidas por falha
    sob_falha = [c for c in condicoes if c != "nominal"]
    tabelas["rq4_recuperacao"] = {}
    for b in ("sma_basico", "sma_local"):
        for c in sob_falha:
            atingidas = [r for r in a(braco=b, condicao=c) if r["t_primeira_falha"] is not None]
            tempos = [r["recuperacao_ticks"] for r in atingidas if r["recuperacao_ticks"] is not None]
            n = len(atingidas)
            tabelas["rq4_recuperacao"].setdefault(b, {})[c] = {
                "execucoes": len(a(braco=b, condicao=c)), "atingidas": n,
                "mesmo_resultado": sum(r["resultado_igual_ao_nominal"] or 0 for r in atingidas),
                "degradacao_segura": sum(r["degradacao_segura"] or 0 for r in atingidas),
                "sem_resposta": sum(1 for r in atingidas if not r["resposta_explicita"]),
                "recuperacao_ticks": {"n": len(tempos), "mediana": estatistica.mediana(tempos) if tempos else None,
                                      "media": round(estatistica.media(tempos), 2) if tempos else None,
                                      "maximo": max(tempos) if tempos else None}}

    def atingidas(braco, conds):
        return [r for r in a(braco=braco, condicao=tuple(conds)) if r["recuperacao_ticks"] is not None
                and r["resposta_explicita"]]

    perdas = [c for c in PERDAS if c in condicoes]
    if "indisponibilidade" in condicoes:
        testes.append(comparar_grupos("RQ4", "sma_basico: perda de mensagens x indisponibilidade", "recuperacao_ticks",
                                      atingidas("sma_basico", perdas), atingidas("sma_basico", ["indisponibilidade"]),
                                      "perda", "indisponibilidade"))
    com_falha = [c for c in FALHAS_DE_COMUNICACAO if c in condicoes]
    testes.append(comparar_grupos("RQ4", "sma_local x sma_basico, falhas de comunicação", "recuperacao_ticks",
                                  atingidas("sma_local", com_falha), atingidas("sma_basico", com_falha),
                                  "sma_local", "sma_basico"))
    # RQ5: porte (bloco A) e parâmetros (bloco B)
    por_porte = ("classificacao_correta", "conformidade_correta", "concluida", "mensagens_coordenacao", "latencia_ticks")
    tabelas["rq5_porte"] = {p: {b: {**{m: descrever(a(braco=b, condicao="nominal", porte=p), m) for m in por_porte},
                                    "execucao_correta_combinadas": descrever(a(braco=b, condicao="combinadas", porte=p),
                                                                             "execucao_correta")}
                                for b in ("sma_basico", "wf_equivalente")} for p in portes}
    for i, p in enumerate(portes):
        for q in portes[i + 1:]:
            for m in ("classificacao_correta", "mensagens_coordenacao"):
                testes.append(comparar("RQ5-porte", f"sma_basico, nominal, {p} x {q}", m,
                                       a(braco="sma_basico", condicao="nominal", porte=p),
                                       a(braco="sma_basico", condicao="nominal", porte=q), p, q))
    B = selecionar(linhas, bloco="B")
    variantes = list(dict.fromkeys(r["variante"] for r in B))
    sensibilidade = ("execucao_correta", "concluida", "resposta_explicita", "classificacao_correta", "criticas_corrigidas",
                     "latencia_ticks", "mensagens_coordenacao", "aprovacoes_expiradas")
    tabelas["rq5_parametros"] = {
        v: {c: {b: {m: descrever(selecionar(B, variante=v, condicao=c, braco=b), m) for m in sensibilidade}
                for b in ("sma_basico", "wf_equivalente") if selecionar(B, variante=v, condicao=c, braco=b)}
            for c in ("nominal", "combinadas")} for v in variantes}

    def do_b(variante, condicao, **f):
        return selecionar(B, variante=variante, condicao=condicao, braco="sma_basico", **f)

    designados = (("max_tentativas=1", "max_tentativas=3", "execucao_correta", "combinadas", {}),
                  ("prazo_subtarefa=15", "prazo_subtarefa=60", "latencia_ticks", "combinadas", {}),
                  ("prazo_aprovacao=10", "prazo_aprovacao=40", "concluida", "combinadas", {"intencao": "fechar_mes"}),
                  ("limiar_percentual=5", "padrao", "classificacao_correta", "nominal", {}),
                  ("limiar_percentual=20", "padrao", "classificacao_correta", "nominal", {}),
                  ("ttl_reserva=40", "padrao", "concluida", "combinadas", {"intencao": "fechar_mes"}),
                  ("max_correcoes=0", "padrao", "criticas_corrigidas", "nominal", {"intencao": "fechar_mes"}))
    for x, y, m, c, f in designados:
        if x in variantes and y in variantes:
            testes.append(comparar("RQ5-parametros", f"sma_basico, {c}, {x} x {y}", m, do_b(x, c, **f), do_b(y, c, **f), x, y))
    # RQ6: ataques sob falha
    tabelas["rq6_ataques"] = {}
    for nome, sel in (("bloco A: ataques ao Approval Gate", selecionar(A, condicao="combinadas_ataque", braco=("sma_basico", "sma_local"))),
                      ("bloco D: com ataques ao controle de acesso", selecionar(D, condicao="combinadas_ataque"))):
        tabelas["rq6_ataques"][nome] = {
            "execucoes": len(sel), "execucoes_atacadas": sum(1 for r in sel if r["ataques_tentados"]),
            "ataques_tentados": sum(r["ataques_tentados"] or 0 for r in sel),
            "ataques_aceitos": sum(r["ataques_aceitos"] or 0 for r in sel),
            "aceitos_sem_a_premissa_do_ataque": sum(r["ataques_sem_premissa"] or 0 for r in sel),
            "aceitos_indevidos": sum((r["ataques_aceitos"] or 0) - (r["ataques_sem_premissa"] or 0) for r in sel),
            "criticas_publicadas_sem_tratamento": sum(r["criticas_publicadas_sem_tratamento"] or 0 for r in sel)}
    if "combinadas_ataque" in condicoes and "combinadas" in condicoes:
        for braco in ("sma_basico", "sma_local"):
            tabelas["rq6_ataques"][f"{braco}: atacada x mesma execução sem ataque"] = _pares_com_assinatura_diferente(
                a(braco=braco, condicao="combinadas_ataque"), a(braco=braco, condicao="combinadas"))
            testes.append(comparar("RQ6", f"{braco}, combinadas_ataque x combinadas", "execucao_correta",
                                   a(braco=braco, condicao="combinadas_ataque"), a(braco=braco, condicao="combinadas"),
                                   "combinadas_ataque", "combinadas"))
    # RQ7: cognição local x básica
    cognicao = ("classificacao_correta", "execucao_correta", "mensagens_coordenacao", "latencia_ticks",
                "sinalizacao_correta", "hipoteses_confirmadas", "hipoteses_refutadas", "hipoteses_arquivadas", "consultas_de_verificacao")
    tabelas["rq7_cognicao"] = {c: {b: {m: descrever(a(braco=b, condicao=c), m) for m in cognicao}
                                   for b in ("sma_basico", "sma_local")} for c in condicoes}
    for c in ("nominal", *perdas, "combinadas"):
        if c in condicoes:
            testes.append(comparar("RQ7", f"sma_local x sma_basico, {c}", "classificacao_correta",
                                   a(braco="sma_local", condicao=c), a(braco="sma_basico", condicao=c),
                                   "sma_local", "sma_basico"))

    def com_pista(braco):
        return [r for r in a(braco=braco, condicao=tuple(perdas)) if "desvio_irregular" in r["plantios"]
                and "observacao_parafraseada" not in r["plantios"]]

    tabelas["rq7_subgrupo_com_pista"] = {b: {m: descrever(com_pista(b), m) for m in cognicao[:4]}
                                         for b in ("sma_basico", "sma_local")}
    testes.append(comparar("RQ7", "sma_local x sma_basico, perda (3 níveis), desvio irregular com pista na planilha",
                           "classificacao_correta", com_pista("sma_local"), com_pista("sma_basico"),
                           "sma_local", "sma_basico"))
    if "perda_media" in condicoes:
        testes.append(comparar("RQ7", "sma_local x sma_basico, perda_media", "mensagens_coordenacao",
                               a(braco="sma_local", condicao="perda_media"), a(braco="sma_basico", condicao="perda_media"),
                               "sma_local", "sma_basico"))
    # ablação (bloco C)
    C = selecionar(linhas, bloco="C")
    ablacao = ("execucao_correta", "resposta_explicita", "concluida", "classificacao_correta", "sinalizacao_correta",
               "criticas_corrigidas",
               "publicacoes_do_periodo", "efeitos_falhos", "mensagens_coordenacao", "latencia_ticks", "reenvios",
               "negociacoes_de_prazo", "hipoteses_confirmadas")
    tabelas["ablacao"] = {v: {c: {i: {m: descrever(selecionar(C, variante=v, condicao=c, intencao=i), m) for m in ablacao}
                                  for i in INTENCOES} for c in CONDICOES_C if selecionar(C, condicao=c)}
                          for v in ABLACAO if selecionar(C, variante=v)}

    def c_(variante, condicao, **f):
        return selecionar(C, variante=variante, condicao=condicao, **f)

    designadas = (("sem_reenvio", "execucao_correta", "perda_media", {}),
                  ("sem_reserva", "publicacoes_do_periodo", "nominal", {"intencao": "fechar_mes"}),
                  ("sem_correcao", "criticas_corrigidas", "nominal", {"intencao": "fechar_mes"}),
                  ("sem_negociacao", "classificacao_correta", "consulta_instavel", {"intencao": "avaliar_orcamento"}),
                  ("sem_cognicao_local", "classificacao_correta", "consulta_instavel", {}))
    for v, m, c, f in designadas:
        if c_(v, c, **f):
            testes.append(comparar("Ablação", f"{v} x completo, {c}" + (f", {f['intencao']}" if f else ""), m,
                                   c_(v, c, **f), c_("completo", c, **f), v, "completo"))
    # invariantes e erros, no experimento inteiro
    sma = [r for r in linhas if r["braco"].startswith("sma")]
    por_invariante: dict[str, int] = {}
    for r in sma:
        for inv in (r["invariantes_violados"] or "").split("|"):
            if inv:
                por_invariante[inv] = por_invariante.get(inv, 0) + 1
    tabelas["invariantes"] = {
        "execucoes_do_sma": len(sma), "execucoes_com_violacao": sum(1 for r in sma if r["violacoes_invariantes"]),
        "execucoes_por_invariante": dict(sorted(por_invariante.items())),
        "avisos_de_prazo_sem_transicao": sum(r["inv03_aviso_sem_transicao"] or 0 for r in sma),
        "sem_resposta_por_condicao": {
            f"{bloco}/{c}": {"execucoes": len(sel), "sem_resposta": sum(1 for r in sel if not r["resposta_explicita"])}
            for bloco in "ABCD" for c in CONDICOES
            if (sel := [r for r in sma if r["bloco"] == bloco and r["condicao"] == c])},
        "execucoes_com_erro": sum(1 for r in linhas if r["status"] == "erro"),
        "ataques_tentados": sum(r["ataques_tentados"] or 0 for r in sma),
        "ataques_aceitos": sum(r["ataques_aceitos"] or 0 for r in sma),
        "ataques_sem_premissa": sum(r["ataques_sem_premissa"] or 0 for r in sma)}
    return {"execucoes": len(linhas), "seeds": sorted({r["seed"] for r in linhas}), "identidade": identidade,
            "tabelas": tabelas, "testes": ajustar(testes), "validacao_estatistica": estatistica.autoteste()}


# ---- saídas -------------------------------------------------------------------------------------
def _csv(caminho, campos, linhas) -> None:
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
        w.writeheader()
        w.writerows({k: ("" if r.get(k) is None else r.get(k)) for k in campos} for r in linhas)


def ler_csv(caminho) -> list[dict]:
    """Lê `execucoes.csv` de volta com os tipos originais (para refazer a análise sem rodar de novo)."""
    texto = {*CHAVE[:5], "variante", "plantios", "perfil_aprovador", "status", "invariantes_violados", "sinalizadas",
             "atribuidas", "correcoes", "erro", "hash"}
    linhas = []
    with open(caminho, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            linhas.append({k: (v if k in texto else None if v == "" else float(v) if "." in v else int(v))
                           for k, v in r.items()})
    return linhas


def manifesto(celulas, replicas, rapido, sha_csv) -> dict:
    por_bloco: dict[str, int] = {}
    for c in celulas:
        por_bloco[c.bloco] = por_bloco.get(c.bloco, 0) + 1
    return {
        "experimento": "DSM4: SMA x workflow centralizado equivalente, sob falhas sorteadas por seed",
        "pre_registro": "docs/dsm4/experimento.md",
        "comando": f"python -m fin_mas experimento --replicas {replicas}" + (" --rapido" if rapido else ""),
        "versao_do_pacote": __version__, "versao_das_normas": versao_normas(), "rapido": rapido,
        "seeds": sorted({c.seed for c in celulas}), "portes": sorted({c.porte for c in celulas}, key=PORTES.index),
        "intencoes": list(INTENCOES), "bracos": dict(ROTULOS),
        "condicoes": {k: {a: (list(map(list, b)) if isinstance(b, tuple) else b) for a, b in v.items()}
                      for k, v in CONDICOES.items() if any(c.condicao == k for c in celulas)},
        "modelo_de_falhas": {"p_plantio": ModeloFalhas(0).p_plantio, "plantios": list(caos.PLANTIOS_BASE),
                             "p_variante_da_observacao": caos.P_VARIANTE_OBSERVACAO,
                             "perfis_do_aprovador": dict(caos.PERFIS), "atraso_do_aprovador_lento": list(caos.ATRASO_HUMANO),
                             "p_aprovador_ausente": caos.P_AUSENTE, "especialistas": list(caos.ESPECIALISTAS),
                             "inicio_da_indisponibilidade": list(caos.INICIO_INDISPONIBILIDADE),
                             "duracao_da_indisponibilidade": list(caos.DURACAO_INDISPONIBILIDADE),
                             "protocolos_sujeitos_a_perda": list(caos.ENTRE_AGENTES)},
        "parametros_padrao": asdict(PADRAO), "varredura": {k: list(v) for k, v in VARREDURA.items()},
        "ablacao": {k: {"parametros": v[0], "cognicao": v[1]} for k, v in ABLACAO.items()},
        "estatistica": {"alfa": ALFA, "reamostragens_bootstrap": estatistica.REAMOSTRAGENS,
                        "semente_bootstrap": estatistica.SEMENTE_BOOTSTRAP, "unidade": "seed",
                        "correcao": "Holm por família"},
        "execucoes": len(celulas), "execucoes_por_bloco": dict(sorted(por_bloco.items())),
        "arquivos": {"execucoes.csv": {"sha256": sha_csv, "reproduzivel": True},
                     "tempo_parede.csv": {"reproduzivel": False,
                                          "nota": "milissegundos de parede por execução; mudam a cada máquina e a cada rodada"}},
    }


def gravar(out, celulas, linhas, tempos, resumo, replicas, rapido) -> dict:
    from fin_mas import estudo_relato
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    _csv(out / "execucoes.csv", CAMPOS, linhas)
    _csv(out / "tempo_parede.csv", [*CHAVE, "ms"], tempos)
    sha = hashlib.sha256((out / "execucoes.csv").read_bytes()).hexdigest()
    m = manifesto(celulas, replicas, rapido, sha)
    for nome, dados in (("manifesto.json", m), ("resumo.json", resumo)):
        (out / nome).write_text(json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "resumo.md").write_text(estudo_relato.resumo_md(resumo, m), encoding="utf-8")
    (out / "testes.md").write_text(estudo_relato.testes_md(resumo), encoding="utf-8")
    for nome, svg in estudo_relato.figuras(resumo).items():
        (out / nome).write_text(svg, encoding="utf-8")
    return m


def rodar(out, replicas: int = 30, rapido: bool = False, progresso=None) -> dict:
    """O experimento inteiro: plano, execução, análise e arquivos em `out`."""
    celulas = plano(replicas, rapido)
    linhas, tempos = executar(celulas, progresso)
    resumo = analisar(linhas)
    m = gravar(out, celulas, linhas, tempos, resumo, replicas, rapido)
    return {"manifesto": m, "resumo": resumo}
