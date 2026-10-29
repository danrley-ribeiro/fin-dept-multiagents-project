# Decisões distribuídas (e não um workflow centralizado)

O feedback pediu evidência de que a interação entre especialistas **produz decisões
distribuídas**. A tabela mostra quem decide cada coisa. O Orquestrador não decide nenhuma
delas: ele roteia o pedido, controla prazos e reenvios e encaminha o veto ao humano.

| Decisão | Quem decide | Com que informação | Como aparece no trace |
|---|---|---|---|
| Qual fonte do realizado vale quando planilha e ERP divergem | AG-ORC | conhecimento da fonte primária (do porte) | `DELIBERA AG-ORC: fonte_confiavel → P-ADOTAR-ERP` |
| Se vale perguntar ao AG-CIN antes de sinalizar um desvio | AG-ORC | crença de desvio acima do limiar e utilidade dos planos | `DELIBERA AG-ORC: explicar_desvio → P-CONSULTAR-CIN` |
| Se o desvio é orçamentário ou um problema de controle | AG-ORC | resposta do AG-CIN (valor contestado) | `INTENCAO ... P-SINALIZAR abandonada` |
| Quais lançamentos inflam uma conta | AG-CIN | crenças sobre lançamentos e efeito orçamentário das violações | `DECISAO AG-CIN: valor contestado = ...` |
| Aprovar, apontar, vetar com correção ou vetar | AG-CIN | crenças, severidade do porte, ciclos de correção | `DELIBERA AG-CIN: parecer → ...` |
| Que correção sugerir | AG-CIN | regras de alçada e quem tem alçada | conteúdo `correcoes_sugeridas` do `veto` |
| Manter ou abandonar o veto após a correção | AG-CIN | nova percepção do ERP ou da planilha | `INTENCAO ... reconsiderada`, nova `DELIBERA` |
| Corrigir, aceitar o risco ou bloquear | humano (APR) | opções oferecidas pelo AG-CIN | `ui decisao_humana` |
| Repetir a delegação ou abortar | AG-ORQ | prazo e número de tentativas (regra fixa) | `DECISAO AG-ORQ: um reenvio ...` |

## Consulta direta entre especialistas

```{mermaid} ../../entregas/dsm2/modelos-editaveis/sequencia_orc_cin.mmd
```

A conversa `QRY-*` entre AG-ORC e AG-CIN é iniciada pelo próprio AG-ORC, sem
participação do Orquestrador (TEST-27). Se a consulta se perde, o AG-ORC replaneja
sozinho (TEST-28); o Orquestrador nem fica sabendo.

## Veto, correção e reavaliação

```{mermaid} ../../entregas/dsm2/modelos-editaveis/sequencia_veto_correcao.mmd
```

O ciclo usa a transição `VETADO --correcao--> EM_ANALISE`, que já existia no `PROT-CMP` da
DSM1 e não estava implementada. Correção, waiver e prazo esgotado agora são **mensagens**
ao AG-CIN, que atualiza crenças e intenções (TEST-30, TEST-31).

## Evidência quantitativa

A métrica {need}`MET-14` (fração das decisões e deliberações tomadas fora do Orquestrador)
fica entre 40% e 85% nos cenários do SMA e é 0% no workflow centralizado, por construção.
Os números estão em {doc}`comparacao`.
