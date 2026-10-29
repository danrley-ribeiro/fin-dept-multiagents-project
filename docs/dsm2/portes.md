# Regras base por porte de empresa

As regras que os agentes aplicam (alçadas, severidade de cada violação, materialidade dos
desvios, fonte primária do realizado, ciclos de correção) e os **pesos dos desejos BDI**
dependem do porte da empresa. Elas vivem em `models/portes.yaml` (versão `normas-v2`), a
base normativa do projeto. Os agentes a percebem pela tool MCP `normas.perfil`: nada disso
fica fixo no código dos agentes.

## Classificação e normas contábeis

| Porte | Critério legal (receita bruta anual) | Norma contábil | Dados |
|---|---|---|---|
| Microempresa (ME) | até R$ 360 mil (LC 123/2006, art. 3º, I) | ITG 1000, modelo simplificado | sem ERP: planilhas (modo manual) |
| Pequeno porte (EPP) | até R$ 4,8 milhões (LC 123/2006, art. 3º, II) | NBC TG 1000 (PMEs) | sistema de gestão simples |
| Média | até R$ 300 milhões (classificação do BNDES) | NBC TG 1000 ou CPCs completos | ERP |
| Grande | acima de R$ 300 milhões; sociedade de grande porte (Lei 11.638/2007, art. 3º) | CPCs completos (Lei 6.404/76) e auditoria independente obrigatória | ERP |

## Regras por porte

| Regra | Micro | Pequena | Média | Grande |
|---|---|---|---|---|
| Quem aprova | sócio | gerente, diretor | gerente, diretor | gerente, diretor |
| Alçada do nível operacional | R$ 2 mil | R$ 3 mil | R$ 10 mil | R$ 20 mil |
| Alçada da gerência | — | R$ 15 mil | R$ 50 mil | R$ 100 mil |
| Alçada da diretoria/sócio | sem limite | sem limite | R$ 200 mil | R$ 500 mil |
| Segregação de funções (SoD) | **não crítica**: controle compensatório (revisão mensal do sócio, COSO 2013) | crítica | crítica | crítica |
| Competência fora do período | não crítica | não crítica | não crítica | **crítica** (corte material) |
| Duplicidade | crítica | crítica | crítica | crítica |
| Materialidade do desvio (NBC TA 320) | 15% e R$ 500 | 12% e R$ 2 mil | 10% e R$ 5 mil | 5% e R$ 50 mil |
| Ciclos de correção antes do bloqueio | 2 | 1 | 1 | 1 |
| Pesos AG-CIN (conformidade : prazo) | 10 : 8 | 10 : 6 | 10 : 5 | 10 : 3 |
| Pesos AG-ORC (precisão : tempestividade) | 2 : 2 | 3 : 2 | 3 : 1 | 4 : 1 |

Os números de alçada e materialidade são **parâmetros de referência** para a simulação,
coerentes com as faixas legais de porte. Uma empresa real ajusta o YAML (ou a aba
*Pessoas* e o porte da planilha) às suas políticas internas.

## Efeitos no comportamento dos agentes

- **Micro sem ERP**: o AG-ORC não reconcilia fontes, porque só existe a planilha; a tool
  `erp.realizado_por_conta` responde "indisponível" e isso aparece no trace. A SoD é
  inevitável (só a sócia aprova) e vira uma ressalva consolidada com o controle
  compensatório. A sócia pode reaprovar um lançamento acima da alçada da assistente.
- **Grande**: a materialidade menor faz o AG-ORC sinalizar desvios que numa média seriam
  ruído; um lançamento em outra competência é crítico e o AG-CIN veta, sugerindo a
  reclassificação.
- **Deliberação**: como a utilidade dos planos soma os pesos dos desejos, a diferença entre
  "vetar com correção" e "vetar" é maior na micro (o prazo pesa mais) do que na grande.

Os cenários `fechamento_micro`, `fechamento_pequena` e `fechamento_grande` exercitam essas
regras; o teste TEST-36 roda os quatro portes e confere, para 10 seeds, que a receita anual
simulada fica na faixa legal do porte.

```bash
python -m fin_mas run --scenario fechar_mes --porte micro
python -m fin_mas run --scenario fechamento_grande
```
