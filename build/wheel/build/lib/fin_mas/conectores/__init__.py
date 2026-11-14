"""Conectores de fonte de dados (ADR-011): ERP simulado, pasta de planilhas, REST JSON genérico, MCP por stdio.

Ver `base.py` (interface e erros), `canonico.py` (modelo canônico e conversões) e
`fontes/entendimento.py` (entendimento automático, determinístico).
"""
from fin_mas.conectores.base import (AmbienteConector, Conector, CredencialRecusada, DadosCanonicos, DadosInvalidos,
                                     ErroConector, FonteIndisponivel, PoliticaRede, RedeNaoLiberada, RespostaInvalida)

TIPOS = ("erp_simulado", "planilhas", "planilha", "rest", "mcp")

__all__ = ["AmbienteConector", "Conector", "CredencialRecusada", "DadosCanonicos", "DadosInvalidos", "ErroConector",
           "FonteIndisponivel", "PoliticaRede", "RedeNaoLiberada", "RespostaInvalida", "TIPOS"]
