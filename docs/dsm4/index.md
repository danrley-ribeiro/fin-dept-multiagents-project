# DSM4 — Experimentação, documentação e entrega final

Entrega final do SMA de Controladoria (prazo 02/12/2026). O pacote para envio é gerado por
`make entrega-dsm4` (`entregas/dsm4/DSM4-entrega.zip`); o README do pacote está em
`entregas/dsm4/README.md` e o relatório técnico em `entregas/dsm4/documentacao/relatorio.pdf`.

| Fechamento da entrega | Conteúdo |
|---|---|
| {doc}`arquitetura-final` | Visão consolidada da arquitetura, quem é BDI e quem é reativo, fluxo de um fechamento, propriedades garantidas e todos os ADRs. |
| {doc}`limitacoes` | O que continua limitado na versão final, sem suavizar, e o que saiu da lista na DSM4. |
| {doc}`demonstracao` | Roteiro de demonstração de 10 minutos com comandos exatos e plano B. |
| {doc}`cenarios-de-teste` | Catálogo dos cenários e dos testes novos da DSM4 (página gerada). |
| {doc}`reproducao` | Passo a passo do zero: instalar, testes, cenários, experimento, documentação, PDF e pacote. |

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

arquitetura-final
demonstracao
reproducao
cenarios-de-teste
limitacoes

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
