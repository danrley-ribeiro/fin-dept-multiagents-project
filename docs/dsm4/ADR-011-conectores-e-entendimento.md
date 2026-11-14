# ADR-011 — Conectores genéricos e entendimento automático de fontes, sem IA generativa

**Status:** aceita (DSM4). **Relaciona-se com:** ADR-002 (LLM opcional por flag), ADR-004 (gateway MCP),
ADR-006 (planilhas e portes), ADR-007 (Approval Gate), ADR-009 (acesso por pessoa).

## Contexto

Até a DSM3 a SMA lia dois tipos de fonte: o dataset sintético (por seed e porte) e uma planilha preenchida no
modelo da SMA (`fontes/planilha.py`), uma por vez. O dono do produto pediu: um arcabouço **genérico**, mais
planilhas para empresas sem ERP, e uma interface que **entenda automaticamente** uma API, um servidor MCP ou uma
planilha **sem IA generativa**; o LLM só é opcional nesses casos. Nenhum conector de fornecedor (SAP, TOTVS...).
Os testes bloqueiam toda rede que não seja loopback: tudo precisa funcionar offline.

## Decisão

1. **Interface `Conector`** (`src/fin_mas/conectores/base.py`): `id`, `tipo`, `capacidades()`, `testar()` →
   diagnóstico por etapas, `ler(competencia)` → dados no **modelo canônico** (`conectores/canonico.py`, o mesmo
   da planilha mais Realizado e Historico) com proveniência lógica por aba, `corrigir()` só para fontes com
   escrita. Implementações: ERP simulado, pasta de planilhas no modelo (várias competências; uma só é o caso
   de `--pasta`), planilha fora do modelo, REST JSON genérico, cliente MCP por stdio.
2. **Integração mínima:** `Ambiente.de_conector()` no molde de `Ambiente.de_pasta()`, e `build_system(ambiente=)`.
   O gateway e a allowlist por agente não mudam: os agentes veem as mesmas tools. Falha da fonte vira
   `mcp_denied` com o motivo e falha explícita ao solicitante (o sistema não trava; cada chamada tenta de novo).
3. **Entendimento determinístico** (`fontes/entendimento.py`): adaptadores de OpenAPI, amostras JSON, tools MCP e
   planilha qualquer (cabeçalho detectado, linha de total separada, aba campo/valor) para uma representação
   comum; inferência de tipos (inteiro, decimal, moeda em reais × centavos, data, competência, identificador,
   booleano, texto); `sugerir_mapeamento` por nome normalizado e sinônimos pt/en, compatibilidade de tipo e
   conteúdo (usuários que existem em Pessoas, contas que existem no Orçamento, códigos únicos), cada sugestão
   com **confiança e motivo legível**; relatório de qualidade e prévia redigida.
4. **Confirmação humana (NORM-30):** o mapeamento só é usado depois de confirmado por uma pessoa com
   PERM-DAD-CONECTAR; a confirmação passa pela validação determinística e fica na trilha com o digest.
5. **LLM opcional (NORM-31):** extensão explícita da NORM-07 a um consumidor de plataforma, o "entendimento de
   fontes". Desligado por padrão; ligado, só **sugere** para campos sem sugestão determinística, recebe só
   nomes e tipos (sem valores), provedor externo exige consentimento, e cada sugestão passa pela mesma
   validação (campo e coluna existem, tipo compatível, mesmo recurso da aba). A sugestão aceita entra com
   confiança baixa, marcada como do LLM, e ainda precisa da confirmação humana. Não grava nada sozinho.
6. **Rede e credenciais (NORM-32):** só loopback por padrão; host externo exige liberação por PERM-DAD-REDE
   (administrador), registrada na trilha. A credencial vai para o **cofre selado** da plataforma (`services/cofre.py`,
   o mesmo do acesso avançado: `ArquivoSelado` com permissão 0600 na pasta de chaves, fora da pasta de dados; garante
   integridade e controle de acesso, não confidencialidade contra quem lê o disco, ver ADR-012) e nunca volta pela
   API, pelo trace ou pela trilha; só é enviada ao host:porta a que foi vinculada no cadastro (trocar a URL
   exige informá-la de novo). Redirecionamentos não são seguidos. Mensagens de erro são redigidas e sem host
   nem porta (vão para o trace, que precisa se repetir).
7. **Escrita continua no Approval Gate:** o ERP de demonstração tem um endpoint de correção, mas só o
   `erp.corrigir` do gateway o alcança, e só com ticket PROT-APR aprovado (ADR-007).
8. **ERP de demonstração** (`conectores/erp_demo.py`, `python -m fin_mas erp-demo`): os dados sintéticos em
   loopback num formato diferente do canônico (campos em inglês, reais com decimais, datas ISO, envelopes e
   paginação, contrato OpenAPI, token), alvo do conector REST e do entendimento.

## Consequências

- Cenários `conector_rest_demo` (resultado igual ao `veto_correcao` sobre o ERP simulado), `conector_fora_do_ar`,
  `planilha_fora_do_modelo` e `mcp_tools_entendidas` (iguais à leitura canônica), repetíveis no
  `cenarios --verificar`; os 140 traces revisados da v0.5.0 seguem idênticos.
- Aba **Fontes de dados** no dashboard; CLI `fontes entender|testar` e `erp-demo`.
- Limitações: o vocabulário de sinônimos é finito e explícito (uma fonte com nomes inesperados cai em "sem
  sugestão" e a pessoa mapeia à mão); não há conector de fornecedor nem exposição em rede; o cliente MCP pelo
  dashboard só sobe o servidor de Excel embutido; o cofre não cifra os valores (o projeto não inventa criptografia: ver ADR-012).
