"""SVC-MEM — memória de longo prazo aprovada, com proveniência, retenção e privacidade (DSM3).

Regras (REQ-F07, NORM-06, NORM-08):

- **só saída aprovada vira memória**: toda gravação cita um ticket PROT-APR que o SVC-POL
  confirma como decidido por um humano, e o ticket precisa corresponder ao que se grava:
  `waiver` exige ticket de waiver aprovado, `correcao` um ticket de correção executado e
  `bloqueio` um ticket rejeitado; a competência é a do ticket e o lançamento está entre os
  achados (ou as correções executadas) daquele veto. Fora disso, a gravação é recusada;
- **identidade**: agentes gravam e consultam por uma visão emitida pelo serviço (`visao`), com
  um token de acesso. Ao confirmar o waiver, o Gate registra os padrões do AG-CIN na própria transação da decisão;
- **proveniência**: aprovação, solicitação, conversa de conformidade, decisão, quem decidiu
  (pseudônimo com chave) e fonte; quem consulta recebe o id `MEM-…`;
- **controle de acesso**: cada tipo de memória tem escritores e leitores;
- **privacidade**: o valor passa por redaction (fail-closed); pessoas viram pseudônimos
  estáveis (`pessoa#…`, HMAC com a chave da memória, que não se reverte por dicionário) e nenhum texto livre com nomes é guardado;
- **retenção**: entradas mais antigas que `retencao` competências expiram na consulta;
- **persistência íntegra**: com `caminho`, a memória é um arquivo JSON gravado de forma atômica.
  Cada entrada leva uma assinatura HMAC-SHA256 e o arquivo inteiro um **selo** HMAC sobre
  (contador de versão, entradas). A chave e o último contador ficam **fora da pasta de dados**
  (`FIN_MAS_DIR_CHAVES` ou `~/.fin_mas/chaves/`; a chave pode vir de `FIN_MAS_CHAVE_MEMORIA`);
- **falha fechada**: arquivo ausente quando já houve gravação, corrompido, com selo que não
  confere, com contador menor que o último gravado (volta a uma versão antiga), em outra versão
  do formato (`VERSAO`; ex.: v3, com pseudônimos sem chave), com entrada
  removida, inventada ou malformada deixa a memória **comprometida**: nada é gravado, a
  consulta informa o estado e o AG-CIN trata todo achado crítico como reincidente, de modo que
  a política não abre waiver até a memória ser restaurada.

DSM4 (ADR-012): o arquivo passa a ser um `ArquivoSelado` (`services/selado.py`) no **mesmo
formato em disco** da v4 (nenhum arquivo existente precisa de migração). Com isso:

- **duas execuções sobre o mesmo arquivo** não perdem entradas: toda gravação e toda expiração
  acontecem dentro da trava entre processos, relendo o arquivo e juntando o que o outro
  processo gravou (antes, a última a gravar sobrescrevia a outra);
- **cópia íntegra em outra pasta**: o selo é conferido com a chave do caminho; uma cópia de
  outra pasta (chave de outro caminho) continua comprometida (falha fechada), mas o motivo diz
  que é uma cópia íntegra e o comando `python -m fin_mas memoria adotar ARQUIVO` (sob
  `PERM-MEM-ADOTAR`, registrado na trilha de acesso) confere selo e assinaturas com a chave de
  origem e passa a usá-la no caminho novo, com contador novo. O mesmo comando aceita, de forma
  explícita e auditada, um backup recolocado no mesmo caminho (contador antigo).
"""
import contextlib
import copy
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import threading
from pathlib import Path

from fin_mas.core.schema import FORMATOS
from fin_mas.services.politica import MOTIVO_REINCIDENCIA
from fin_mas.services.redacao import FalhaRedacao, redigir
from fin_mas.services.selado import ArquivoComprometido, ArquivoSelado, TravaOcupada, _estado, pasta_de_chaves, trava

VERSAO = 4  # v4: pseudônimo com HMAC (chave da memória) em vez de SHA-256 sem chave
RETENCAO_COMPETENCIAS = 12
# tipo -> (quem grava, quem lê). As entradas são do AG-CIN: correção e bloqueio ele grava ao receber a decisão
# humana validada; o waiver é gravado em nome dele pelo SVC-POL, na decisão, sob a trava (POL-06). A leitura
# segue o menor privilégio (DSM4, ADR-010): correção aprovada é um fato sobre os dados (um lançamento saiu
# ou mudou), que o AG-ORC e o AG-RES precisam para interpretar desvio e indicador, e o AG-REL para contar o
# histórico; waiver e bloqueio são decisões de risco sobre um veto e continuam só com quem veta (AG-CIN): o
# relatório já recebe do Orquestrador o waiver do período. O AG-CUS não lê nada: nenhum critério de rateio
# depende de decisão do Approval Gate. Pedido de leitura fora desta tabela é negado e registrado (`negada`).
ACESSO = {
    "waiver": ({"AG-CIN"}, {"AG-CIN"}),
    "correcao": ({"AG-CIN"}, {"AG-CIN", "AG-ORC", "AG-RES", "AG-REL"}),
    "bloqueio": ({"AG-CIN"}, {"AG-CIN"}),
}
EXIGE = {  # tipo -> (decisão do ticket, estados aceitos)
    "waiver": ("waiver", {"aprovado", "executado"}),
    "correcao": ("corrigir", {"executado"}),
    "bloqueio": ("bloquear", {"rejeitado"}),
}
COMPETENCIA = FORMATOS["aaaa-mm"][0]  # mesma regra do barramento e do dashboard (core/schema.py)
CAMPOS = {"id": str, "tipo": str, "chave": str, "valor": dict, "competencia": str, "agente": str,
          "proveniencia": dict, "assinatura": str}


class MemoriaRecusada(PermissionError):
    pass


class _SemMudanca(Exception):
    """Transação sem alteração: não grava (o contador só sobe quando algo mudou)."""


class _ArquivoMemoria(ArquivoSelado):
    """`ArquivoSelado` no formato em disco da memória v4: entradas no topo e selo sobre (contador, entradas)."""

    def __init__(self, caminho, chave: bytes):
        super().__init__(caminho, "memoria", VERSAO, {"entradas": []}, chave=chave)

    def _selo(self, contador: int, dados: dict) -> str:
        return _selo_memoria(self._chave, contador, dados["entradas"])

    def _decodificar(self, bruto: dict) -> tuple:
        if not isinstance(bruto.get("entradas"), list):
            raise KeyError("entradas")
        return bruto["versao"], bruto["contador"], {"entradas": bruto["entradas"]}, bruto["selo"]

    def _gravar(self, rascunho, contador):
        # Um waiver pode criar várias entradas na mesma transação. O contador preserva
        # o maior ID mesmo se uma manutenção expirar todas as entradas depois.
        maior = max((int(e["id"][4:]) for e in rascunho["entradas"]), default=0)
        super()._gravar(rascunho, max(contador, maior))

    def _codificar(self, contador: int, dados: dict, selo: str) -> dict:
        return {"versao": self.versao, "contador": contador, "entradas": dados["entradas"], "selo": selo}


def _selo_memoria(chave: bytes, contador, entradas) -> str:
    corpo = json.dumps({"contador": contador, "entradas": entradas}, sort_keys=True, ensure_ascii=False)
    return hmac.new(chave, corpo.encode("utf-8"), hashlib.sha256).hexdigest()


PSEUDONIMO = re.compile(r"pessoa#[0-9a-f]{10}")


def _sem_pseudonimo(valor):
    """Tira o pseudônimo dos registros do trace: ele depende da chave local da memória (mudaria o
    hash do trace entre máquinas) e não acrescenta nada ao auditor, que já vê os usuários do ERP
    como evidência de alçada e SoD. A entrada da memória (`MEM-…`) continua identificada."""
    if isinstance(valor, str):
        return PSEUDONIMO.sub("pessoa#…", valor)
    if isinstance(valor, dict):
        return {k: _sem_pseudonimo(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_sem_pseudonimo(v) for v in valor]
    return valor




def _meses(competencia: str) -> int:
    return int(competencia[:4]) * 12 + int(competencia[5:7])


def _reincide(mes: int, competencia: str, retencao: int) -> bool:
    """POL-06: outra competência (não a mesma) a até `retencao` meses, antes ou depois."""
    return 0 < abs(mes - _meses(competencia)) <= retencao


def _canonico(entrada: dict) -> bytes:
    return json.dumps({k: v for k, v in entrada.items() if k != "assinatura"}, sort_keys=True,
                      ensure_ascii=False).encode("utf-8")


class Memoria:
    ID = "SVC-MEM"

    def __init__(self, audit, clock, politica=None, caminho=None, retencao: int = RETENCAO_COMPETENCIAS):
        self.audit = audit
        self.clock = clock
        self.politica = politica
        self.caminho = Path(caminho) if caminho else None
        self.retencao = retencao
        self.entradas: list[dict] = []
        self._acessos: dict[str, str] = {}  # agente -> token da visão emitida
        self.comprometida: str | None = None  # motivo, quando a integridade do arquivo não pôde ser garantida
        self.contador = 0
        self._trava_local = threading.RLock()
        self._ultimo_id = 0  # maior número de MEM-… já emitido neste processo (ids nunca são reaproveitados)
        self._chave = self._carregar_chave()
        self._arquivo = _ArquivoMemoria(self.caminho, self._chave) if self.caminho else None
        if self.caminho:
            self._carregar()

    @property
    def integra(self) -> bool:
        return self.comprometida is None

    def pseudonimo(self, valor: str) -> str:
        """Pseudônimo estável de uma pessoa: HMAC com a chave da memória (fora da pasta de dados).

        Sem a chave não dá para refazer a tabela nome -> pseudônimo, mesmo com poucos usuários
        no ERP; com a mesma chave o pseudônimo se repete entre execuções (reincidência).
        """
        return "pessoa#" + hmac.new(self._chave, f"pseudonimo:{valor}".encode("utf-8"),
                                    hashlib.sha256).hexdigest()[:10]

    # ---- identidade -------------------------------------------------------------------
    def visao(self, agente: str) -> "VisaoMemoria":
        """Emite a visão do agente (uma por agente): só ela grava e consulta em nome dele."""
        if agente in self._acessos:
            raise MemoriaRecusada(f"visão de {agente} já emitida")
        self._acessos[agente] = secrets.token_hex(16)
        return VisaoMemoria(self, agente, self._acessos[agente])

    def _autentico(self, agente, token) -> bool:
        esperado = self._acessos.get(agente)
        return esperado is not None and isinstance(token, str) and hmac.compare_digest(esperado, token)

    # ---- escrita ------------------------------------------------------------------
    def gravar(self, agente: str, tipo: str, chave: str, valor: dict, *, competencia: str, aprovacao: str,
               fonte: str, cid: str | None = None, token: str | None = None) -> dict:
        try:
            if not self._autentico(agente, token):
                raise MemoriaRecusada(f"{agente}: identidade não autenticada (use a visão emitida pelo SVC-MEM)")
            if self.comprometida:
                raise MemoriaRecusada(f"memória comprometida ({self.comprometida}): restaure o arquivo antes de gravar")
            if tipo not in ACESSO or agente not in ACESSO[tipo][0]:
                raise MemoriaRecusada(f"{agente} não grava memória do tipo {tipo}")
            ticket = self.politica.tickets.get(aprovacao) if self.politica else None
            decisao, estados = EXIGE[tipo]
            if ticket is None or ticket["estado"] not in estados or ticket["decisao"] != decisao:
                raise MemoriaRecusada(f"NORM-08: {aprovacao!r} não é uma decisão humana de {decisao} registrada")
            if competencia != ticket["competencia"]:
                raise MemoriaRecusada(f"NORM-08: competência {competencia} difere da do ticket ({ticket['competencia']})")
            validos = ({x["lancamento"] for x in ticket.get("executadas", [])} if tipo == "correcao"
                       else {a["lancamento"] for a in ticket.get("achados", [])})
            if not isinstance(valor, dict) or valor.get("lancamento") not in validos:
                raise MemoriaRecusada(f"NORM-08: lançamento {valor.get('lancamento') if isinstance(valor, dict) else None}"
                                      f" não pertence à decisão {aprovacao}")
            try:
                valor = redigir(valor)
            except FalhaRedacao as erro:
                raise MemoriaRecusada(f"NORM-06: sanitização falhou ({erro})") from erro
        except MemoriaRecusada as erro:
            self._registrar(cid, "recusada", agente=agente, tipo=tipo, chave=chave, motivo=str(erro))
            raise
        try:
            with self._sob_trava():  # relê dentro da trava: o que outro processo gravou entra antes
                repetida = next((e for e in self.entradas if (e["tipo"], e["chave"], e["competencia"],
                                                              e["proveniencia"]["aprovacao"]) ==
                                 (tipo, chave, competencia, aprovacao)), None)
                if repetida:
                    return repetida
                entrada = self._inserir(agente, tipo, chave, valor, competencia, aprovacao, fonte, ticket)
        except MemoriaRecusada as erro:
            self._registrar(cid, "recusada", agente=agente, tipo=tipo, chave=chave, motivo=str(erro))
            raise
        self._registrar(cid, "gravada", agente=agente, memoria=entrada["id"], tipo=tipo, chave=chave,
                        competencia=competencia, aprovacao=aprovacao)
        return entrada

    def _inserir(self, agente, tipo, chave, valor, competencia, aprovacao, fonte, ticket):
        # nunca reaproveita um id: além do maior existente, o maior já emitido neste processo e o
        # contador selado do arquivo, relido dentro da trava (cada gravação o incrementa, inclusive
        # a de outro processo), que sobrevive a entradas expiradas
        existentes = max((int(e["id"][4:]) for e in self.entradas if e["id"][4:].isdigit()), default=0)
        selado = self._arquivo._contador if self._arquivo is not None else self.contador
        proximo = max(existentes, self._ultimo_id, selado) + 1
        self._ultimo_id = proximo
        entrada = {
            "id": f"MEM-{proximo:04d}", "tipo": tipo, "chave": chave, "valor": valor,
            "competencia": competencia, "agente": agente,
            "proveniencia": {"aprovacao": aprovacao, "solicitacao": ticket["solicitacao"], "cmp": ticket["cmp"],
                             "decisao": ticket["decisao"],
                             "decidido_por": self.pseudonimo(ticket["aprovado_por"]["pessoa"])
                             if ticket.get("aprovado_por") else None, "fonte": fonte},
        }
        entrada["assinatura"] = self._assinar(entrada)
        self.entradas.append(entrada)
        return entrada

    def _decidir_waiver(self, ticket, padroes, aprovador):
        """Confere todos os padrões e registra a decisão em uma transação. O endosso apenas consulta."""
        competencia = ticket["competencia"]
        mes = _meses(competencia)
        novas = []
        try:  # redação antes da trava: uma falha aqui não deixa gravação pela metade
            valores = {chave: redigir(valor) for chave, valor in padroes.items()}
        except FalhaRedacao as erro:
            return f"POL-06: histórico de decisões indisponível ({erro})"
        antes, ultimo_id = list(self.entradas), self._ultimo_id
        try:
            with self._sob_trava():
                for e in self.entradas:
                    # mesma regra da oferta (`consultar(..., janela="outras")`): waiver do mesmo padrão em outra
                    # competência dentro da retenção, antes ou depois. Antes a decisão contava também o mesmo mês e
                    # a oferta só os meses anteriores: o waiver era oferecido e depois recusado (reexecução do mês
                    # com a mesma memória; em lote, o ticket ficava sem resposta até o prazo)
                    if e["tipo"] == "waiver" and e["chave"] in padroes and _reincide(mes, e["competencia"], self.retencao):
                        lado = "anterior" if _meses(e["competencia"]) < mes else "posterior"
                        return f"{MOTIVO_REINCIDENCIA}: waiver {lado} {e['id']} em {e['competencia']}"
                if aprovador is not None:
                    decisao = dict(ticket, decisao="waiver", aprovado_por=aprovador)
                    ja = {e["chave"] for e in self.entradas if e["tipo"] == "waiver" and e["competencia"] == competencia}
                    for chave, valor in valores.items():
                        if chave in ja:  # mesmo mês já liberado (reexecução com a mesma memória): não duplica
                            continue
                        novas.append(self._inserir("AG-CIN", "waiver", chave, valor, competencia,
                                                  ticket["id"], f"PROT-APR {ticket['id']}", decisao))
        except (MemoriaRecusada, OSError) as erro:
            # nada foi gravado; sem arquivo, as entradas inseridas ficariam só em memória e bloqueariam waivers futuros
            self.entradas, self._ultimo_id = antes, ultimo_id
            return f"POL-06: histórico de decisões indisponível ({erro})"
        for e in novas:
            self._registrar(ticket["cmp"], "gravada", agente="AG-CIN", memoria=e["id"], tipo="waiver",
                            chave=e["chave"], competencia=competencia, aprovacao=ticket["id"])
        return None

    # ---- leitura --------------------------------------------------------------------
    def consultar(self, agente: str, tipo: str, chave: str | None = None, *, competencia_atual: str,
                  cid: str | None = None, token: str | None = None, janela: str = "anteriores") -> list[dict]:
        """Entradas do tipo (e chave) dentro da retenção: de competências anteriores (`janela="anteriores"`) ou
        de qualquer outra competência, antes ou depois (`janela="outras"`: a regra da POL-06, a mesma que a
        decisão do waiver confere em `_decidir_waiver`).

        A retenção é um filtro desta consulta: nada é apagado aqui. Antes, a consulta apagava do arquivo
        tudo o que estivesse fora da janela da competência *pedida*; um pedido de `2099-12` apagava o
        waiver de 2026 e, com ele, a POL-06. A remoção física é a manutenção explícita `expirar`.
        """
        if not self._autentico(agente, token) or tipo not in ACESSO or agente not in ACESSO[tipo][1]:
            self._registrar(cid, "negada", agente=agente, tipo=tipo, chave=chave)
            return []
        if self._arquivo is not None and not self.comprometida:
            # relê o arquivo dentro da trava, sem gravar (nada muda: `_SemMudanca`): o que outro processo gravou
            # entra na consulta. Antes isso vinha de carona no `expirar` chamado aqui, que também apagava; sem a
            # releitura, um waiver gravado por outro processo não seria visto e a POL-06 deixaria passar a
            # reincidência. Fora da trava, no Windows, a leitura segurava o arquivo aberto e o `os.replace` de
            # quem gravava falhava (uma entrada perdida com quatro execuções simultâneas)
            try:
                with self._sob_trava():
                    pass
            except MemoriaRecusada:
                pass  # comprometida (a consulta responde "indisponível" abaixo) ou ocupada: usa o que já tem
        if self.comprometida:
            self._registrar(cid, "indisponivel", agente=agente, tipo=tipo, motivo=self.comprometida)
            return []
        atual = _meses(competencia_atual)

        def na_janela(e) -> bool:
            if janela == "outras":
                return _reincide(atual, e["competencia"], self.retencao)
            return atual - self.retencao <= _meses(e["competencia"]) < atual

        achadas = [e for e in self.entradas if e["tipo"] == tipo and (chave is None or e["chave"] == chave)
                   and na_janela(e)]
        if achadas:
            self._registrar(cid, "consultada", agente=agente, tipo=tipo, chave=chave,
                            memorias=[e["id"] for e in achadas])
        return achadas

    def expirar(self, competencia_atual: str, cid: str | None = None) -> None:
        """Manutenção: remove do arquivo as entradas fora da retenção em relação a `competencia_atual`.
        Não é chamada por consulta nem por pedido (ver `consultar`)."""
        limite = _meses(competencia_atual) - self.retencao
        vencidas = []
        try:
            with self._sob_trava():
                vencidas = [e for e in self.entradas if _meses(e["competencia"]) < limite]
                if vencidas:
                    self.entradas = [e for e in self.entradas if e not in vencidas]
        except MemoriaRecusada:
            return  # memória comprometida ou ocupada: a consulta seguinte informa o estado
        if vencidas:
            self._registrar(cid, "expirada", agente=self.ID, memorias=[e["id"] for e in vencidas],
                            retencao=self.retencao)

    def limpar(self, ator: str | None, cid: str | None = None) -> int:
        """Administração: apaga todas as entradas (o histórico de reincidência recomeça) e devolve quantas eram.

        Reiniciar um cenário NÃO limpa a memória (correção simulada da DSM4: no dashboard de demonstração a memória
        vivia só no processo e um reinício esquecia o waiver anterior). Limpar é um ato separado, de quem tem
        `PERM-MEM-LIMPAR` (administrador, que não aprova), feito sob a trava e registrado no trace com o autor.
        Memória comprometida não é limpa: a restauração é `memoria adotar` ou o backup."""
        with self._sob_trava():
            apagadas = [e["id"] for e in self.entradas]
            self.entradas = []
        self._registrar(cid, "limpa", agente=self.ID, ator=ator, memorias=apagadas)
        return len(apagadas)

    # ---- persistência e integridade ---------------------------------------------------------
    def _arquivo_estado(self, sufixo: str) -> Path:
        base = Path(os.environ.get("FIN_MAS_DIR_CHAVES") or Path.home() / ".fin_mas" / "chaves")
        nome = hashlib.sha256(str(self.caminho.resolve()).encode("utf-8")).hexdigest()[:16]
        return base / f"memoria-{nome}.{sufixo}"

    def _carregar_chave(self) -> bytes:
        if os.environ.get("FIN_MAS_CHAVE_MEMORIA"):
            return os.environ["FIN_MAS_CHAVE_MEMORIA"].encode("utf-8")
        if not self.caminho:
            return secrets.token_bytes(32)  # memória só em processo: chave efêmera
        arquivo = self._arquivo_estado("chave")  # fora da pasta de dados
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        # criação atômica: dois processos no primeiro uso não podem gerar chaves diferentes (ver selado.chave_de)
        try:
            fd = os.open(arquivo, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            for _ in range(200):
                chave = arquivo.read_bytes()
                if len(chave) >= 32:
                    return chave
                time.sleep(0.01)
            raise ArquivoComprometido(f"chave da memória incompleta em {arquivo.name}") from None
        chave = secrets.token_bytes(32)
        with os.fdopen(fd, "wb") as f:
            f.write(chave)
        return chave

    def _assinar(self, entrada: dict) -> str:
        return hmac.new(self._chave, _canonico(entrada), hashlib.sha256).hexdigest()

    def _selar(self, contador: int, entradas: list) -> str:
        return _selo_memoria(self._chave, contador, entradas)

    def _ultimo_contador(self) -> int:
        try:
            return int(self._arquivo_estado("contador").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0

    def _comprometer(self, motivo: str) -> None:
        if self.comprometida is None:
            self.comprometida = motivo
            self._registrar(None, "comprometida", agente=self.ID, motivo=motivo,
                            arquivo=self.caminho.name if self.caminho else None)

    def _carregar(self) -> None:
        try:
            dados = self._arquivo.ler()
        except ArquivoComprometido as erro:
            self._diagnosticar(str(erro))
            return
        if not self.caminho.exists():
            return  # memória nova: nada gravado ainda
        self.contador = self._arquivo._contador
        self.entradas = self._validas(dados["entradas"])
        self._registrar(None, "carregada", agente=self.ID, entradas=len(self.entradas), arquivo=self.caminho.name,
                        integra=self.integra)

    def _validas(self, brutas) -> list:
        validas = []
        for e in brutas:
            motivo = self._invalida(e)
            if motivo:
                self._registrar(None, "descartada", agente=self.ID,
                                memoria=e.get("id") if isinstance(e, dict) else None, motivo=motivo)
                self._comprometer(f"entrada inválida: {motivo}")
            else:
                validas.append(e)
        return validas

    def _diagnosticar(self, motivo_selado: str) -> None:
        """O `ArquivoSelado` recusou o arquivo: descobre o motivo para o auditor e carrega, só para leitura do
        diagnóstico, as entradas que ainda têm assinatura válida (a memória fica comprometida de qualquer jeito)."""
        esperado = self._ultimo_contador()
        if not self.caminho.exists():
            self._comprometer(f"arquivo ausente, mas a versão {esperado} já foi gravada")
            return
        try:
            dados = json.loads(self.caminho.read_text(encoding="utf-8"))
            if not isinstance(dados, dict) or not isinstance(dados.get("entradas"), list):
                raise ValueError("estrutura inesperada")
        except (ValueError, OSError) as erro:
            self._registrar(None, "descartada", agente=self.ID, motivo=f"arquivo ilegível: {erro}")
            self._comprometer(f"arquivo ilegível: {erro}")
            return
        if dados.get("versao") != VERSAO:
            # outro formato (ex.: v3, pseudônimo sem chave): as chaves de reincidência não casam com as
            # consultas desta versão e a POL-06 deixaria de valer. Não há migração (os nomes não ficam
            # guardados), então a memória fica comprometida (falha fechada). Apagar só o arquivo não basta:
            # o contador fora da pasta de dados acusaria arquivo ausente; o caminho é começar outro arquivo.
            self._comprometer(f"arquivo na versão {dados.get('versao')!r} do formato, esta é a {VERSAO}: "
                              "chaves de reincidência de outra versão não são reconhecidas; "
                              "comece uma memória nova (outro arquivo em --memoria)")
            return
        contador, brutas = dados.get("contador"), dados["entradas"]
        if not isinstance(contador, int) or not hmac.compare_digest(str(dados.get("selo")),
                                                                    _selo_memoria(self._chave, contador, brutas)):
            if isinstance(contador, int) and _chave_que_sela(dados) is not None:
                self._comprometer("cópia íntegra de outra pasta (selada com a chave de outro caminho): confira a "
                                  "origem e adote com `python -m fin_mas memoria adotar " + self.caminho.name + "`")
            else:
                self._comprometer("selo do arquivo não confere (entrada removida, inserida ou arquivo alterado)")
        elif contador < esperado:
            self._comprometer(f"versão {contador} é anterior à última gravada ({esperado}): arquivo antigo restaurado "
                              f"(para aceitar o backup de propósito: `python -m fin_mas memoria adotar`)")
        else:
            self._comprometer(motivo_selado)
        self.contador = contador if isinstance(contador, int) else 0
        self.entradas = self._validas(brutas)
        self._registrar(None, "carregada", agente=self.ID, entradas=len(self.entradas), arquivo=self.caminho.name,
                        integra=self.integra)

    @contextlib.contextmanager
    def _sob_trava(self):
        """Alteração das entradas. Com arquivo: trava entre processos, relê e confere o arquivo, entrega
        `self.entradas` atualizadas para o bloco alterar e grava ao sair (só se algo mudou)."""
        if self._arquivo is None:
            with self._trava_local:
                yield
            return
        if self.comprometida:
            raise MemoriaRecusada(f"memória comprometida ({self.comprometida}): restaure o arquivo antes de gravar")
        try:
            with self._arquivo.transacao() as dados:
                atuais = self._validas(dados["entradas"])
                if self.comprometida:
                    raise MemoriaRecusada(f"memória comprometida ({self.comprometida})")
                self.entradas = atuais
                antes = copy.deepcopy(atuais)
                yield
                if self.entradas == antes:
                    raise _SemMudanca
                dados["entradas"] = copy.deepcopy(self.entradas)
        except _SemMudanca:
            pass
        except ArquivoComprometido as erro:
            self._comprometer(str(erro))
            raise MemoriaRecusada(f"memória comprometida ({erro})") from None
        except TravaOcupada as erro:
            raise MemoriaRecusada(f"memória em uso por outro processo, tente de novo: {erro}") from None
        self.contador = self._arquivo._contador

    def _invalida(self, e) -> str | None:
        if not isinstance(e, dict):
            return "entrada não é objeto"
        for campo, tipo in CAMPOS.items():
            if not isinstance(e.get(campo), tipo):
                return f"campo {campo} ausente ou de tipo errado"
        if e["tipo"] not in ACESSO or not COMPETENCIA.fullmatch(e["competencia"]):
            return "tipo ou competência inválidos"
        if not isinstance(e["proveniencia"].get("aprovacao"), str):
            return "proveniência sem aprovação"
        if not hmac.compare_digest(e["assinatura"], self._assinar(e)):
            return "assinatura não confere (entrada alterada fora do SVC-MEM)"
        if not re.fullmatch(r"MEM-[0-9]+", e["id"]):
            return "id de memória inválido"
        return None

    def _registrar(self, cid, evento, **campos) -> None:
        self.audit.record(self.clock(), "memoria", conversation_id=cid, evento=evento, **_sem_pseudonimo(campos))


class VisaoMemoria:
    """O que o agente enxerga do SVC-MEM: grava e consulta com a própria identidade e o token da visão."""

    def __init__(self, servico: Memoria, agente: str, token: str):
        self._servico = servico
        self._agente = agente
        self.__token = token

    def gravar(self, tipo, chave, valor, **kw) -> dict:
        return self._servico.gravar(self._agente, tipo, chave, valor, token=self.__token, **kw)

    def consultar(self, tipo, chave=None, **kw) -> list[dict]:
        return self._servico.consultar(self._agente, tipo, chave, token=self.__token, **kw)

    def pseudonimo(self, valor: str) -> str:
        return self._servico.pseudonimo(valor)

    @property
    def integra(self) -> bool:
        return self._servico.integra

    @property
    def motivo_comprometida(self) -> str | None:
        return self._servico.comprometida

    def resumo(self) -> dict:
        return {"entradas": len(self._servico.entradas), "persistente": self._servico.caminho is not None,
                "integra": self._servico.integra}


# ---- adoção de um arquivo íntegro (DSM4) ----------------------------------------------------------
def _chaves_conhecidas() -> list[bytes]:
    chaves = []
    if os.environ.get("FIN_MAS_CHAVE_MEMORIA"):
        chaves.append(os.environ["FIN_MAS_CHAVE_MEMORIA"].encode("utf-8"))
    pasta = pasta_de_chaves()
    if pasta.is_dir():
        chaves += [p.read_bytes() for p in sorted(pasta.glob("memoria-*.chave"))]
    return chaves


def _chave_que_sela(bruto: dict) -> bytes | None:
    """Chave conhecida (desta máquina) que confere o selo e todas as assinaturas do arquivo, ou None."""
    for chave in _chaves_conhecidas():
        if not hmac.compare_digest(str(bruto.get("selo")), _selo_memoria(chave, bruto.get("contador"), bruto["entradas"])):
            continue
        if all(isinstance(e, dict) and isinstance(e.get("assinatura"), str) and hmac.compare_digest(
                e["assinatura"], hmac.new(chave, _canonico(e), hashlib.sha256).hexdigest()) for e in bruto["entradas"]):
            return chave
    return None


def adotar(caminho, *, forcar: bool = False) -> dict:
    """Adota no lugar um arquivo de memória íntegro: cópia de outra pasta ou backup recolocado (contador antigo).

    Confere o formato, o selo e as assinaturas com uma chave conhecida desta máquina; passa a usar essa chave
    no caminho do arquivo (pseudônimos e reincidência continuam valendo) e grava de novo com contador maior
    que qualquer um já visto. Quem chama confere a permissão (`PERM-MEM-ADOTAR`) e registra na trilha.
    """
    caminho = Path(caminho)
    with trava(caminho):
        return _adotar_sob_trava(caminho, forcar)


def _adotar_sob_trava(caminho, forcar):
    try:
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
        if not isinstance(bruto, dict) or not isinstance(bruto.get("entradas"), list) \
                or not isinstance(bruto.get("contador"), int):
            raise ValueError("estrutura inesperada")
    except (OSError, ValueError) as erro:
        raise MemoriaRecusada(f"{caminho.name}: não é um arquivo de memória legível ({erro})") from None
    if bruto.get("versao") != VERSAO:
        raise MemoriaRecusada(f"{caminho.name}: versão {bruto.get('versao')!r} do formato; só a versão {VERSAO} é "
                              f"adotada (outra versão tem chaves de reincidência incompatíveis)")
    chave = _chave_que_sela(bruto)
    if chave is None:
        raise MemoriaRecusada(f"{caminho.name}: nenhuma chave desta máquina confere o selo e as assinaturas: não é "
                              f"uma memória íntegra deste sistema (alterada ou de outra instalação)")
    arquivo_chave = _estado("memoria", caminho, "chave")
    arquivo_contador = _estado("memoria", caminho, "contador")
    try:
        ultimo = int(arquivo_contador.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ultimo = 0
    da_env = bool(os.environ.get("FIN_MAS_CHAVE_MEMORIA")) and chave == os.environ["FIN_MAS_CHAVE_MEMORIA"].encode("utf-8")
    atual = arquivo_chave.read_bytes() if arquivo_chave.exists() else None
    troca = not da_env and atual is not None and atual != chave
    if troca and ultimo > 0 and not forcar:
        raise MemoriaRecusada(f"{caminho.name}: este caminho já tem outra memória gravada ({ultimo} gravação(ões)) com "
                              f"outra chave; para substituí-la de propósito, use --forcar")
    if not da_env and atual != chave:
        arquivo_chave.parent.mkdir(parents=True, exist_ok=True)
        arquivo_chave.write_bytes(chave)
        with contextlib.suppress(OSError):
            os.chmod(arquivo_chave, 0o600)
    selado = _ArquivoMemoria(caminho, chave)
    selado._gravar({"entradas": bruto["entradas"]}, max(bruto["contador"], ultimo) + 1)
    return {"arquivo": str(caminho), "entradas": len(bruto["entradas"]), "contador": selado._contador,
            "origem": "outra pasta" if atual != chave and not da_env else "este caminho (backup recolocado)",
            "chave_substituida": troca, "contador_anterior": ultimo}
