# DSM4 — Experimentação, documentação e entrega final

Páginas da DSM4 disponíveis até aqui.

| Página | Conteúdo |
|---|---|
| {doc}`experimento` | Pré-registro: perguntas, hipóteses, braços, fatores, métricas, plano de análise e ameaças previstas. Versionado antes de existir qualquer resultado. |
| {doc}`resultados` | O que foi medido, em duas rodadas (antes e depois da correção do defeito que a primeira revelou): resposta a cada pergunta, comportamento coletivo, o que não se confirmou, defeitos encontrados, desvios do pré-registro e ameaças à validade. |
| {doc}`tabelas` | Todas as tabelas e todos os testes de hipótese da segunda rodada, gerados pelo comando do experimento. |
| {doc}`cognicao` | Especialistas BDI, aprendizado local, estratégias de compromisso e base normativa. |
| {doc}`implantacao` | Um comando, Docker, pacote instalável, backup e restauração. |
| {doc}`portes-e-segmentos` | MEI, Média empresa II e os segmentos (comércio, serviços, indústria). |
| {doc}`acesso-avancado` | Segundo fator, alçada por pessoa, delegação, dupla aprovação, cofre e várias empresas. |
| {doc}`ADR-011-conectores-e-entendimento` | Conectores genéricos e entendimento automático de fontes, sem IA generativa. |

```bash
python -m fin_mas experimento --replicas 30 --out docs/dsm4/resultados   # ou: make experimento (cerca de 3 minutos)
python -m fin_mas experimento --rapido --out /tmp/experimento            # 3 seeds, alguns segundos
```

```{toctree}
:maxdepth: 1

experimento
resultados
tabelas
cognicao
ADR-010-especialistas-bdi
implantacao
portes-e-segmentos
acesso-avancado
ADR-012-acesso-avancado
ADR-011-conectores-e-entendimento
```
