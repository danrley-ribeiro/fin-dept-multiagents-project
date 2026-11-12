"""SVC-MOD — Registro de Modelos e gateway de LLM opcional (ADR-002, NORM-05, NORM-07), DSM3.

O LLM só **acrescenta** uma síntese ao relatório do AG-REL; os números continuam vindo
do template determinístico. Regras:

- flag desligada por padrão; LLM só em AG-REL, AG-RES e AG-ORC (NORM-07) — configurar
  outro agente levanta `ConfiguracaoInvalida`;
- modelo, limite de tokens e cota trocam em tempo de execução e valem na próxima chamada;
- cota esgotada bloqueia a chamada antes de enviá-la; o agente segue no template;
- todo número do texto gerado precisa existir no texto-base (template); número divergente
  ou proposta de ação descartam o texto (NORM-05) e ficam registrados como fallback;
- com a flag ligada, cada chamada gera registro de prompt (`llm_prompt`) e de custo
  (`llm_custo`); com ela desligada, nada é registrado e o custo é zero.

Provedores offline (deterministas, usados nos testes e na demonstração): `mock-narrador`,
`mock-alucina` (altera um número) e `mock-acao` (sugere uma ação). O provedor real
`claude-opus-5-5` usa o SDK `anthropic`, se instalado, e só roda com a flag ligada e
credencial configurada; qualquer erro dele também cai no template.
"""
import re
from decimal import Decimal, InvalidOperation

PERMITIDOS = {"AG-REL", "AG-RES", "AG-ORC"}
VERSAO_PROMPT = "prompt-sintese-v1"
MODELO_REAL = "claude-opus-5-5"
PRECO_POR_MILHAO = {MODELO_REAL: (4.00, 20.00)}  # US$ entrada / saída; mocks custam zero
SISTEMA = ("Você escreve a síntese executiva de um relatório de controladoria. Use só os números que aparecem "
           "no relatório, exatamente como estão escritos. Não recomende nem aprove ações. Até 3 frases, em português.")
ACAO = re.compile(r"\b(aprov[ae]r?|aprove|estorn[ae]r?|estorne|execut[ae]r?|execute|lan[cç]ar|lance|liberar?|libere)\b",
                  re.IGNORECASE)
NUMERO = re.compile(r"\d[\d.,]*")


class ConfiguracaoInvalida(ValueError):
    pass


def valor_numerico(token: str):
    """Valor de um número escrito em pt-BR (`.` de milhar, `,` decimal): 1.234,56 -> 1234.56.

    A escala importa: `12.345,6` e `123.456` são valores diferentes de `1.234,56`. Um formato
    que não dá para interpretar volta como texto e só confere se aparecer igual no texto-base.
    """
    t = token.rstrip(".,")
    if t.count(",") == 1:
        inteiro, decimal = t.split(",")
        if inteiro.count(".") and not all(len(g) == 3 for g in inteiro.split(".")[1:]):
            return t
        t = inteiro.replace(".", "") + "." + decimal
    elif "," in t:
        return t
    elif t.count(".") >= 1 and all(len(g) == 3 for g in t.split(".")[1:]):
        t = t.replace(".", "")  # 1.388.886 (milhar)
    elif t.count(".") > 1:
        return t
    try:
        return Decimal(t).normalize()
    except InvalidOperation:
        return t


def numeros(texto: str) -> set:
    """Valores numéricos do texto (R$ 1.234,56 -> 1234.56; 12,5% -> 12.5), comparados pelo valor."""
    return {valor_numerico(n) for n in NUMERO.findall(texto)}


def _narrador(prompt: str, texto_base: str) -> str:
    linhas = [x for x in texto_base.splitlines() if ":" in x and not x.startswith(("Ressalva", "Nota"))][:4]
    return "Síntese: " + "; ".join(linhas) + "."


def _alucina(prompt, texto_base):
    texto = _narrador(prompt, texto_base)
    return NUMERO.sub(lambda m: m.group(0)[:-1] + str((int(m.group(0)[-1]) + 1) % 10), texto, count=1)


def _acao(prompt, texto_base):
    return _narrador(prompt, texto_base) + " Recomendo aprovar o estorno no ERP."


def _mock(fn):
    def provedor(modelo, prompt, texto_base, max_tokens):
        texto = fn(prompt, texto_base)
        return texto, {"entrada": len(prompt.split()), "saida": len(texto.split())}
    return provedor


def _anthropic(modelo, prompt, texto_base, max_tokens):
    import anthropic  # dependência opcional: sem o SDK, a chamada falha e o template prevalece

    client = anthropic.Anthropic()
    resposta = client.beta.messages.create(
        model=modelo, max_tokens=max_tokens, system=SISTEMA,
        messages=[{"role": "user", "content": prompt}],
        output_config={"effort": "low"},  # síntese curta: esforço baixo basta
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
    )
    if resposta.stop_reason == "refusal":
        raise RuntimeError("o modelo recusou a síntese")
    texto = "".join(b.text for b in resposta.content if b.type == "text").strip()
    return texto, {"entrada": resposta.usage.input_tokens, "saida": resposta.usage.output_tokens}


PROVEDORES = {"mock-narrador": _mock(_narrador), "mock-alucina": _mock(_alucina), "mock-acao": _mock(_acao),
              MODELO_REAL: _anthropic}


class RegistroModelos:
    ID = "SVC-MOD"

    def __init__(self, audit, clock, provedores: dict | None = None):
        self.audit = audit
        self.clock = clock
        self.provedores = dict(provedores or PROVEDORES)
        self.configs: dict[str, dict] = {}

    def config(self, agente: str) -> dict:
        return self.configs.setdefault(agente, {"llm": False, "modelo": "mock-narrador", "max_tokens": 2000,
                                                "cota_tokens": 20_000, "usado": 0})

    def configurar(self, agente: str, **campos) -> dict:
        """Altera a configuração em tempo de execução; vale a partir da próxima chamada."""
        desconhecidos = set(campos) - {"llm", "modelo", "max_tokens", "cota_tokens"}
        if desconhecidos:
            raise ConfiguracaoInvalida(f"campos desconhecidos: {sorted(desconhecidos)}")
        if campos.get("llm") and agente not in PERMITIDOS:
            raise ConfiguracaoInvalida(f"NORM-07: LLM não é permitido em {agente} (só {sorted(PERMITIDOS)})")
        if "modelo" in campos and campos["modelo"] not in self.provedores:
            raise ConfiguracaoInvalida(f"modelo desconhecido: {campos['modelo']}")
        cfg = self.config(agente)
        cfg.update(campos)
        self.audit.record(self.clock(), "modelo", agente=agente, evento="configurado",
                          config={k: v for k, v in cfg.items() if k != "usado"})
        return cfg

    def gerar(self, agente: str, cid: str, tarefa: str, texto_base: str) -> str | None:
        """Síntese validada, ou None (flag desligada, cota, erro ou texto reprovado: usar só o template)."""
        cfg = self.config(agente)
        if not cfg["llm"] or agente not in PERMITIDOS:
            return None
        prompt = f"Tarefa: {tarefa}. Relatório:\n{texto_base}"
        estimativa = len(prompt.split()) + cfg["max_tokens"]
        if cfg["usado"] + estimativa > cfg["cota_tokens"]:
            self._fallback(agente, cid, cfg, f"cota esgotada ({cfg['usado']} de {cfg['cota_tokens']} tokens)")
            return None
        self.audit.record(self.clock(), "llm_prompt", conversation_id=cid, agente=agente, modelo=cfg["modelo"],
                          versao_prompt=VERSAO_PROMPT, sistema=SISTEMA, prompt=prompt)
        try:
            texto, uso = self.provedores[cfg["modelo"]](cfg["modelo"], prompt, texto_base, cfg["max_tokens"])
        except Exception as erro:
            self._fallback(agente, cid, cfg, f"provedor indisponível: {type(erro).__name__}: {erro}")
            return None
        cfg["usado"] += uso["entrada"] + uso["saida"]
        entrada, saida = PRECO_POR_MILHAO.get(cfg["modelo"], (0.0, 0.0))
        custo = round((uso["entrada"] * entrada + uso["saida"] * saida) / 1_000_000, 6)
        self.audit.record(self.clock(), "llm_custo", conversation_id=cid, agente=agente, modelo=cfg["modelo"],
                          tokens_entrada=uso["entrada"], tokens_saida=uso["saida"], custo_usd=custo,
                          acumulado_tokens=cfg["usado"])
        estranhos = sorted((str(n) for n in numeros(texto) - numeros(texto_base)))
        if estranhos:
            self._fallback(agente, cid, cfg, f"NORM-05: números ausentes do núcleo determinístico: {estranhos}")
            return None
        if ACAO.search(texto):
            self._fallback(agente, cid, cfg, f"NORM-05: o texto propõe uma ação ({ACAO.search(texto).group(0)})")
            return None
        return texto

    def _fallback(self, agente, cid, cfg, motivo) -> None:
        self.audit.record(self.clock(), "llm_fallback", conversation_id=cid, agente=agente, modelo=cfg["modelo"],
                          motivo=motivo)
