"""Conector REST JSON genérico (sem nada de fornecedor específico).

Configuração (o que a pessoa cadastra; a credencial fica no cofre, nunca aqui):

    {"url_base": "http://127.0.0.1:8790",
     "autenticacao": {"tipo": "bearer" | "cabecalho" | "query" | "nenhuma",
                      "cabecalho": "X-API-Key", "parametro": "api_key"},
     "tempo_limite": 10,
     "openapi": "/openapi.json",                     # opcional: contrato para descobrir os recursos
     "recursos": {"journal-entries": {"caminho": "/api/v1/journal-entries?period={competencia}",
                                       "raiz": "data",
                                       "paginacao": {"parametro": "page", "tamanho_parametro": "page_size",
                                                     "tamanho": 50, "mais": "has_more"}}},
     "escrita": {"caminho": "/api/v1/journal-entries/{lancamento}/actions",
                 "corpo": {"action": "{acao}", "period": "{competencia}"},
                 "acoes": {"estornar": "reverse", "reaprovar": "reapprove", "reclassificar": "reclassify"}},
     "competencia": "2026-09", "porte": "media"}

Rede: só loopback, salvo host liberado por um administrador (`PoliticaRede`). Redirecionamentos
não são seguidos (um servidor local não consegue desviar a chamada para fora). Toda falha vira
`ErroConector` com mensagem redigida e sem host nem porta (a mensagem pode ir para o trace, que
precisa ser o mesmo em duas execuções).
"""
import json
import socket
import urllib.error
import urllib.request
from urllib.parse import quote, urlencode, urlsplit, urlunsplit, parse_qsl

from fin_mas.conectores.base import (TEMPO_LIMITE, ConectorMapeado, CredencialRecusada, ErroConector,
                                     FonteIndisponivel, PoliticaRede, RespostaInvalida, diagnostico, etapa)

TAMANHO_MAXIMO = 20 * 1024 * 1024
MAX_PAGINAS = 200
AUTENTICACOES = ("nenhuma", "bearer", "cabecalho", "query")


class _SemRedirecionar(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirecionamento recusado", headers, fp)


_ABRIDOR = urllib.request.build_opener(_SemRedirecionar())


def raiz_de(dados, raiz: str | None):
    """Lista de registros dentro da resposta: `raiz` (ex.: "data" ou "resultado.itens") ou a própria resposta."""
    atual = dados
    for parte in [p for p in (raiz or "").split(".") if p]:
        if not isinstance(atual, dict) or parte not in atual:
            raise RespostaInvalida(f"raiz {raiz!r} ausente na resposta")
        atual = atual[parte]
    if isinstance(atual, dict):
        return [atual]
    if not isinstance(atual, list) or not all(isinstance(x, dict) for x in atual):
        raise RespostaInvalida(f"a raiz {raiz or '(resposta)'} não é uma lista de objetos")
    return atual


class ConectorREST(ConectorMapeado):
    tipo = "rest"

    def __init__(self, id: str, config: dict, segredo: str | None = None, mapeamento: dict | None = None,
                 politica: PoliticaRede | None = None, host_credencial: str | None = None):
        """`host_credencial`: host:porta a que a credencial foi vinculada quando foi guardada (padrão: o da
        `url_base`). A credencial só vai para esse host; mudou a URL, é preciso informá-la de novo."""
        super().__init__(id, mapeamento, porte=config.get("porte"))
        self.config = config
        self.__segredo = segredo
        self.politica = politica or PoliticaRede()
        self.host_credencial = (host_credencial or urlsplit(str(config.get("url_base") or "")).netloc).lower()
        auth = (config.get("autenticacao") or {}).get("tipo", "nenhuma")
        if auth not in AUTENTICACOES:
            raise ValueError(f"autenticação desconhecida: {auth} (use {', '.join(AUTENTICACOES)})")
        if not str(config.get("url_base") or "").startswith(("http://", "https://")):
            raise ValueError("url_base precisa começar com http:// ou https://")

    @property
    def tempo_limite(self) -> float:
        return float(self.config.get("tempo_limite") or TEMPO_LIMITE)

    def capacidades(self) -> set:
        return {"leitura", "competencias"} | ({"escrita"} if self.config.get("escrita") else set())

    def competencia_padrao(self):
        return self.config.get("competencia")

    def descricao(self) -> dict:
        return {**super().descricao(), "recursos": sorted(self.config.get("recursos") or {})}

    # ---- HTTP --------------------------------------------------------------------------------
    def _credencial_para(self, url: str) -> str | None:
        """O segredo só acompanha pedidos ao host a que foi vinculado (nunca a outro destino)."""
        if not self.__segredo or urlsplit(url).netloc.lower() != self.host_credencial:
            return None
        return self.__segredo

    @property
    def credencial_vinculada(self) -> bool:
        return bool(self.__segredo) and urlsplit(self.config["url_base"]).netloc.lower() == self.host_credencial

    def _url(self, caminho: str, extra: dict | None = None) -> str:
        base = self.config["url_base"].rstrip("/")
        if "://" in caminho or caminho.startswith("//"):
            raise RespostaInvalida("caminho de recurso precisa ser relativo à URL base")
        partes = urlsplit(base + "/" + caminho.lstrip("/"))
        q = parse_qsl(partes.query, keep_blank_values=True) + list((extra or {}).items())
        auth = self.config.get("autenticacao") or {}
        segredo = self._credencial_para(base)
        if auth.get("tipo") == "query" and segredo:
            q.append((auth.get("parametro") or "api_key", segredo))
        return urlunsplit((partes.scheme, partes.netloc, partes.path, urlencode(q), ""))

    def _cabecalhos(self, url: str) -> dict:
        h = {"Accept": "application/json", "User-Agent": "fin-mas-conector"}
        auth = self.config.get("autenticacao") or {}
        segredo = self._credencial_para(url)
        if segredo and auth.get("tipo") == "bearer":
            h["Authorization"] = f"Bearer {segredo}"
        elif segredo and auth.get("tipo") == "cabecalho":
            h[auth.get("cabecalho") or "X-API-Key"] = segredo
        return h

    def _erro(self, classe, mensagem):
        return classe(mensagem, segredos=(self.__segredo,))

    def pedir(self, caminho: str, metodo: str = "GET", corpo: dict | None = None, extra: dict | None = None,
              rotulo: str | None = None):
        """JSON de `caminho`. `rotulo` nomeia o recurso nas mensagens (nunca host e porta)."""
        url = self._url(caminho, extra)
        self.politica.verificar(url)
        rotulo = rotulo or urlsplit(caminho).path
        dados = None if corpo is None else json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        cab = self._cabecalhos(url) | ({"Content-Type": "application/json"} if dados is not None else {})
        pedido = urllib.request.Request(url, data=dados, method=metodo, headers=cab)
        try:
            with _ABRIDOR.open(pedido, timeout=self.tempo_limite) as r:  # noqa: S310 (host conferido acima)
                bruto = r.read(TAMANHO_MAXIMO + 1)
        except urllib.error.HTTPError as e:
            detalhe = e.read(300).decode("utf-8", "replace") if e.fp else ""
            if e.code in (401, 403):
                raise self._erro(CredencialRecusada, f"{rotulo}: credencial recusada pela fonte (HTTP {e.code}) "
                                                     f"{detalhe}") from None
            if 300 <= e.code < 400:
                raise self._erro(RespostaInvalida, f"{rotulo}: a fonte respondeu com redirecionamento "
                                                   f"(HTTP {e.code}), que não é seguido") from None
            if e.code >= 500:
                raise self._erro(FonteIndisponivel, f"{rotulo}: erro na fonte (HTTP {e.code}) {detalhe}") from None
            raise self._erro(RespostaInvalida, f"{rotulo}: HTTP {e.code} {detalhe}") from None
        except (socket.timeout, TimeoutError):
            raise self._erro(FonteIndisponivel, f"{rotulo}: tempo esgotado ({self.tempo_limite:g} s)") from None
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise self._erro(FonteIndisponivel, f"{rotulo}: tempo esgotado ({self.tempo_limite:g} s)") from None
            raise self._erro(FonteIndisponivel, f"{rotulo}: fonte fora do ar (conexão recusada ou endereço "
                                                "inalcançável)") from None
        except (ConnectionError, OSError):
            raise self._erro(FonteIndisponivel, f"{rotulo}: conexão interrompida pela fonte") from None
        except AssertionError:  # rede bloqueada pelo ambiente (testes offline)
            raise self._erro(FonteIndisponivel, f"{rotulo}: rede indisponível neste ambiente") from None
        if len(bruto) > TAMANHO_MAXIMO:
            raise self._erro(RespostaInvalida, f"{rotulo}: resposta maior que {TAMANHO_MAXIMO // 1024 // 1024} MB")
        try:
            return json.loads(bruto.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise self._erro(RespostaInvalida, f"{rotulo}: a resposta não é JSON válido") from None

    # ---- leitura ---------------------------------------------------------------------------
    def ler_recurso(self, recurso: str, competencia: str | None) -> list[dict]:
        spec = (self.config.get("recursos") or {}).get(recurso)
        if spec is None:
            raise RespostaInvalida(f"recurso não configurado: {recurso}")
        caminho = spec["caminho"].replace("{competencia}", quote(competencia or ""))
        pag = spec.get("paginacao")
        if not pag:
            return raiz_de(self.pedir(caminho, rotulo=recurso), spec.get("raiz"))
        registros, pagina = [], int(pag.get("inicio", 1))
        for _ in range(int(pag.get("max_paginas", MAX_PAGINAS))):
            extra = {pag.get("parametro", "page"): pagina}
            if pag.get("tamanho_parametro"):
                extra[pag["tamanho_parametro"]] = pag.get("tamanho", 50)
            resposta = self.pedir(caminho, extra=extra, rotulo=recurso)
            lote = raiz_de(resposta, spec.get("raiz"))
            registros += lote
            mais = resposta.get(pag.get("mais", "has_more")) if isinstance(resposta, dict) else False
            if not mais or not lote:
                return registros
            pagina += 1
        raise self._erro(RespostaInvalida, f"{recurso}: mais de {pag.get('max_paginas', MAX_PAGINAS)} páginas")

    def amostras(self, competencia: str | None) -> dict:
        """Uma página de cada recurso, para o entendimento automático (sem converter nada)."""
        saida = {}
        for nome, spec in (self.config.get("recursos") or {}).items():
            caminho = spec["caminho"].replace("{competencia}", quote(competencia or ""))
            saida[nome] = self.pedir(caminho, rotulo=nome)
        return saida

    def contrato(self) -> dict | None:
        return self.pedir(self.config["openapi"], rotulo="contrato OpenAPI") if self.config.get("openapi") else None

    def testar(self) -> dict:
        etapas = []
        try:
            self.politica.verificar(self.config["url_base"])
            etapas.append(etapa("rede", True, "endereço permitido (loopback ou liberado por um administrador)"))
        except ErroConector as e:
            return {**diagnostico([etapa("rede", False, str(e))]), "rede_bloqueada": True}
        if self.__segredo and not self.credencial_vinculada:
            etapas.append(etapa("credencial", False, "a credencial guardada foi vinculada a outro endereço e não é "
                                                     "enviada a este: informe-a de novo"))
        if self.config.get("openapi"):
            try:
                spec = self.contrato()
                etapas.append(etapa("contrato", True, f"OpenAPI {spec.get('openapi', '?')}: "
                                                      f"{len(spec.get('paths') or {})} caminhos"))
                if not self.config.get("recursos"):  # sem recursos cadastrados: os do contrato
                    from fin_mas.fontes.entendimento import de_openapi
                    self.config["recursos"] = {r["nome"]: r["descritor"] for r in de_openapi(spec)["recursos"]}
            except ErroConector as e:
                etapas.append(etapa("contrato", False, str(e)))
                return diagnostico(etapas)
        competencia = self.competencia_padrao()
        for nome in sorted(self.config.get("recursos") or {}):
            try:
                n = len(self.ler_recurso(nome, competencia))
                etapas.append(etapa(f"recurso {nome}", True, f"{n} registro(s)"))
            except ErroConector as e:
                etapas.append(etapa(f"recurso {nome}", False, str(e)))
                if isinstance(e, (CredencialRecusada, FonteIndisponivel)):
                    break
        if not self.config.get("recursos"):
            etapas.append(etapa("recursos", False, "nenhum recurso configurado: rode o entendimento da fonte"))
        return diagnostico(etapas)

    # ---- escrita (correção aprovada) ---------------------------------------------------------
    def corrigir(self, competencia: str, lancamento: str, acao: str) -> dict:
        escrita = self.config.get("escrita")
        if not escrita:
            return super().corrigir(competencia, lancamento, acao)
        valor = (escrita.get("acoes") or {}).get(acao)
        if valor is None:
            raise ErroConector(f"a fonte não oferece a correção {acao}")
        caminho = escrita["caminho"].replace("{lancamento}", quote(lancamento, safe=""))
        corpo = {k: (v.replace("{acao}", valor).replace("{competencia}", competencia).replace("{lancamento}", lancamento)
                     if isinstance(v, str) else v) for k, v in (escrita.get("corpo") or {}).items()}
        resposta = self.pedir(caminho, metodo=escrita.get("metodo", "POST"), corpo=corpo, rotulo="correção")
        detalhe = resposta.get("detail") or resposta.get("detalhe") if isinstance(resposta, dict) else None
        return {"lancamento": lancamento, "acao": acao, "detalhe": detalhe or f"{lancamento}: {acao} aplicado na fonte"}
