# Implantação: um comando, pacote, contêiner, backup e migração

<span class="badge-ok">implementado</span> · DSM4

O SMA de Controladoria roda **numa máquina só, para quem está nela**. Há três formas de implantar,
com o mesmo programa e a mesma pasta de dados: do checkout (um comando), pelo pacote instalável e
por contêiner. Exposição em rede ou nuvem está **fora do escopo por decisão do dono do produto**:
o servidor escuta em loopback e recusa `Host`/`Origin` que não sejam `127.0.0.1` ou `localhost`
(proteção contra DNS rebinding e páginas de outros sites), e nenhuma das três formas muda isso.

## 1. Um comando (checkout do repositório)

```bash
python3 tools/iniciar.py            # prepara .venv, bun, dashboard e sobe o escritório ao vivo
python -m fin_mas instalar          # assistente: porte, segmento, cognição, administrador
python -m fin_mas serve --instalacao dados
python -m fin_mas doctor --pasta dados
```

O assistente pergunta o **porte** (`mei`, `micro`, `pequena`, `media`, `media_ii`, `grande`) e o
**segmento** (`software_servicos`, `comercio`, `servicos`, `industria`; ver
{doc}`portes-e-segmentos`). Sem terminal interativo, as respostas vêm das opções
(`--porte`, `--segmento`, `--cognicao`, `--usuario`) e a senha do administrador de
`FIN_MAS_SENHA_NOVA`; com `--demo`, são criadas as contas de demonstração (senha pública).

## 2. Pacote instalável (wheel, pip ou pipx)

```bash
make wheel                                   # constrói o dashboard (bun) e gera dist/fin_mas-1.0.0-py3-none-any.whl
pipx install dist/fin_mas-1.0.0-py3-none-any.whl
fin-mas instalar --pasta ~/sma-dados && fin-mas serve --instalacao ~/sma-dados
```

Os modelos YAML (`models/*.yaml`) e o build do dashboard (`web/dist`) viajam **dentro do pacote**,
em `fin_mas/_dados/`, lidos com `importlib.resources` (`src/fin_mas/recursos.py`). `models_dir()` e
o diretório do dashboard procuram primeiro os dados do pacote e, no checkout (modo
desenvolvimento, `PYTHONPATH=src`), caem em `models/` e `web/dist/` da raiz. O repositório não
guarda cópias: `tools/empacotar_wheel.py` copia o código para `build/wheel/`, põe ali os YAML e o
dashboard e chama `pip wheel` (o setuptools vem do isolamento de build do pip). O teste
`test_wheel_installs_in_a_clean_venv_and_runs_outside_the_repository` instala o wheel num venv
limpo e roda, numa pasta fora do repositório, `fin-mas list`, `fin-mas run --scenario fechar_mes`
(mesmo hash do checkout), `fin-mas instalar --demo` e `fin-mas doctor`. Sem rede, o teste instala o
wheel com `--no-deps` e aponta para as dependências de runtime (pyyaml, openpyxl, et_xmlfile) do
ambiente que roda os testes. `fin-mas doctor` mostra de onde vêm os modelos: `(pacote)` ou
`(checkout)`.

Dependências de runtime continuam só `pyyaml` e `openpyxl`; `textual` (`fin-mas[tui]`) e
`anthropic` (`fin-mas[llm]`) são extras opcionais.

## 3. Contêiner (Docker e Compose)

```bash
cp .env.example .env        # defina FIN_MAS_SENHA_NOVA, ou FIN_MAS_DEMO=1 só para avaliação
docker compose up -d --build
# abra http://localhost:8765
docker compose run --rm sma doctor --pasta /dados
```

- **`Dockerfile`**, em três estágios: build do dashboard com `oven/bun:1.4.2` (mesma versão que
  gerou `web/bun.lock`), wheel com `tools/empacotar_wheel.py` e runtime `python:3.13-slim` com o
  wheel instalado, usuário `sma` (uid 10001, sem privilégios) e `HEALTHCHECK` em `/api/saude`.
  Compatível com o builder clássico do Docker (sem recursos exclusivos do BuildKit).
- **`docker/entrada.sh`**: na primeira subida roda `fin-mas instalar` em `/dados` (porte,
  segmento e cognição das variáveis abaixo) e depois `fin-mas serve --instalacao /dados --host
  0.0.0.0 --porta 8765`. Outros comandos vão direto ao `fin-mas`.
- **`compose.yaml`**: porta publicada **só em `127.0.0.1:8765`** do hospedeiro; volume `dados`
  (`/dados`) e volume `chaves` (`/chaves`, `FIN_MAS_DIR_CHAVES`) separados; `.env` opcional;
  sistema de arquivos somente leitura (com `/tmp` em memória), `cap_drop: ALL`,
  `no-new-privileges` e healthcheck.
- **`--host`**: o `serve` passou a aceitar `--host`. Dentro do contêiner ele escuta em `0.0.0.0`
  (sem isso a porta publicada não alcança o processo), mas a checagem de `Host`/`Origin` de
  loopback **continua valendo**: o navegador do hospedeiro entra por `http://localhost:8765`, e
  um pedido com `Host: sma.exemplo.com` recebe 403 (teste
  `test_server_on_all_interfaces_still_accepts_only_loopback_names`). Publicar a porta em outra
  interface ou pôr um proxy na frente é exposição em rede, fora do escopo.

**O que foi verificado nesta máquina.** A imagem foi construída de verdade (`docker build`, motor
Docker 29.5.2 no colima) e executada com as mesmas opções do `compose.yaml` (`docker run` com
porta em `127.0.0.1`, os dois volumes, `--read-only`, `--tmpfs /tmp`, `--cap-drop ALL`,
`no-new-privileges`): saúde 200 e estado `healthy`, `Host` externo recusado (403), login de
demonstração, página do dashboard, reinício com segmento pela API e um fechamento publicado,
`doctor` e `run` dentro do contêiner, gravação recusada fora de `/dados`. O **Docker Compose não
foi executado**: o plugin `docker compose` desta máquina é um link quebrado para um Docker Desktop
removido. O `compose.yaml` foi validado pela leitura do YAML no teste
`test_container_files_publish_only_on_loopback_and_keep_keys_apart` (porta só em loopback,
volumes, variáveis, endurecimento e healthcheck), não pelo `docker compose config`.

## 4. Backup, restauração e migração

```bash
fin-mas backup --pasta dados --para backup.zip --chaves-para backup.chaves.zip
fin-mas restaurar backup.zip --pasta dados-novos --chaves backup.chaves.zip
fin-mas migrar --pasta dados [--simular]
```

- **Backup**: `backup.zip` tem `manifesto.json` (SHA-256 e tamanho de cada arquivo e quais
  arquivos de estado ele tem na pasta de chaves) e os dados em `dados/`. O manifesto é **selado**
  com HMAC por uma chave de backup que fica, como as outras, fora da pasta de dados. As chaves
  só saem com `--chaves-para`, num **arquivo separado** (modo 0600): guarde-o em outro lugar;
  quem tem os dois arquivos tem tudo.
- **Restauração** (falha fechada, código 3, nada é gravado no destino se algo não conferir): o
  zip só pode ter o manifesto e `dados/...` (sem caminhos absolutos nem `..`); o selo do
  manifesto confere com a chave de backup; cada arquivo confere com o hash; numa pasta
  temporária, com uma pasta de chaves temporária, os arquivos selados são lidos pelas classes de
  sempre (`ArquivoSelado` para o cadastro, `TrilhaAcesso.verificar()` para a cadeia e a cabeça da
  trilha, `Memoria` para selo e assinaturas da memória). Só então os dados vão para a pasta nova.
- **Restaurar em outra pasta.** Os arquivos de estado se chamam
  `<rotulo>-<sha256(caminho absoluto)[:16]>.<sufixo>` (`services/selado.py::_estado`): o caminho
  entra no **nome** (cada arquivo tem a sua chave e o seu contador), mas o segredo é o
  **conteúdo**. A restauração copia o mesmo conteúdo para o nome derivado do caminho novo, e só
  depois de os selos conferirem com a chave original, então ela não serve para fazer o sistema
  aceitar dados forjados. Ela se recusa se já existir estado para algum caminho de destino:
  restaurar por cima de uma instalação que existiu nesta máquina seria um **rollback**, que é o
  que o contador fora da pasta existe para impedir. A pasta e as chaves de origem não são
  tocadas. Na mesma máquina, `--chaves` é dispensável (as chaves da origem estão lá); em outra,
  é obrigatório.
- **Migração**: os arquivos selados têm versão de formato (hoje 1 no cadastro de contas e de
  sessões). `migrar` confere o selo na versão em que o arquivo está, aplica em cadeia as funções
  registradas em `fin_mas.manutencao.MIGRACOES[(rotulo, versao)]` e grava selado na versão nova,
  dentro da trava e com contador novo. **Hoje não há o que migrar** (`MIGRACOES` está vazio e
  todos os arquivos estão na versão atual); o mecanismo é exercido por uma migração de exemplo
  1→2 registrada só no teste `test_migration_mechanism_with_an_example_from_version_1_to_2`, que
  também mostra que o sistema na versão 1 recusa (IAM-07) o arquivo migrado e que um arquivo de
  versão mais nova não é "migrado para trás". A memória do SVC-MEM (versão 4) não tem migração
  possível: os pseudônimos são HMAC sem volta.

Testes: `tests/integration/test_backup_restauracao.py` (restauração em outra pasta e com outra
pasta de chaves; arquivo trocado, hash corrigido, manifesto re-selado, fuga de diretório, arquivo
a mais, chaves de outra instalação e rollback recusados).

## 5. Variáveis de ambiente

| Variável | Para quê |
|---|---|
| `FIN_MAS_DIR_CHAVES` | pasta das chaves de integridade, contadores e cabeças das trilhas (padrão `~/.fin_mas/chaves`; `/chaves` no contêiner) |
| `FIN_MAS_SENHA_NOVA` | senha do administrador criado pelo `instalar` sem terminal (tire do `.env` depois da primeira subida) |
| `FIN_MAS_ADMIN` | usuário desse administrador no contêiner (padrão `admin`) |
| `FIN_MAS_DEMO` | `1` = contas de demonstração (senha pública), só para avaliação |
| `FIN_MAS_PORTE`, `FIN_MAS_SEGMENTO`, `FIN_MAS_COGNICAO` | porte, segmento e cognição da primeira subida do contêiner |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `FIN_MAS_LLM_API_KEY` | chaves dos provedores de LLM (opcionais; o LLM vem desligado) |
| `FIN_MAS_LLM_URLS_CONFIAVEIS` | URLs, além da padrão de cada provedor, para as quais uma chave de LLM pode ser enviada (ex.: servidor local compatível com a OpenAI) |
| `FIN_MAS_CHAVE_MEMORIA` | chave fixa da memória do SVC-MEM (testes); sem ela, a chave fica na pasta de chaves |

## 6. O que cada pasta guarda

| Pasta | Conteúdo |
|---|---|
| `<dados>/acesso/` | `contas.json` e `sessoes.json` selados (SVC-IAM) e `trilha.jsonl` encadeada |
| `<dados>/empresa/` | a planilha da empresa enviada pelo dashboard (fonte da competência sem ERP) |
| `<dados>/modelos/` | modelo em branco e o exemplo preenchido do porte e do segmento escolhidos |
| `<dados>/instalacao.json` | porte, segmento, cognição, porta e cenário (lido pelo `serve --instalacao`) |
| `FIN_MAS_DIR_CHAVES` | `<rotulo>-<hash do caminho>.chave`, `.contador` e `.cabeca` de cada arquivo selado e a chave de backup; **nunca** dentro da pasta de dados |

**Chaves fora da pasta de dados.** Copiar a pasta de dados para outra máquina não leva as chaves:
lá o cadastro é recusado (falha fechada, IAM-07). O caminho certo é `backup` com `--chaves-para` e
`restaurar` com `--chaves`. No contêiner, os dois volumes ficam separados pelo mesmo motivo.
