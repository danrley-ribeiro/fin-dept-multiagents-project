"""Console de administração de acesso e de auditoria no terminal (Textual), ADR-009.

    python -m fin_mas acesso --acesso PASTA tui

A TUI é para **gerenciar**: contas, papéis, sessões, trilha de acesso e traces gravados. A
plataforma (a simulação dos agentes) é usada pelo dashboard web. As duas leem e gravam os mesmos
arquivos selados: o que o administrador faz aqui vale no servidor na requisição seguinte.

O Textual é dependência opcional (extra `tui`). Este módulo importa sem ele; só `executar`
precisa da biblioteca, e sem ela explica como instalar em vez de mostrar um traceback.
"""
import sys


def executar(pasta_acesso, custo_scrypt: int = 15) -> int:
    """Roda o console sobre o cadastro em `pasta_acesso`. Devolve 0, ou 2 se o Textual não está instalado."""
    try:
        import textual  # noqa: F401  (tardio: o pacote `fin_mas.tui` existe mesmo sem o extra)
    except ImportError:
        print('o console de administração precisa do Textual: pip install "fin-mas[tui]"\n'
              "os mesmos recursos existem na linha de comando: python -m fin_mas acesso --help "
              "(usuario, papeis, sessao, trilha)", file=sys.stderr)
        return 2
    from fin_mas.tui.app import ConsoleAcesso
    try:
        app = ConsoleAcesso(pasta_acesso, custo_scrypt=custo_scrypt)
    except OSError as erro:
        print(f"não foi possível abrir o cadastro de acesso em {pasta_acesso}: {erro}", file=sys.stderr)
        return 1
    try:
        app.run()
    finally:
        app.encerrar_sessao()  # se o console caiu no meio, a sessão do administrador não fica aberta
    return app.return_code or 0
