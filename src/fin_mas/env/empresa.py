"""Empresa fictícia SMA S.A.: perfil fixo usado pelo dataset, relatórios e dashboard.

Todos os nomes são inventados; nenhum dado pertence a empresa real. O perfil não
consome o gerador aleatório, então valores gerados por seed não mudam com ele.
"""

EMPRESA = {
    "sigla": "SMA",
    "razao_social": "SMA S.A.",
    "descricao": "Empresa fictícia de software e serviços usada nos cenários sintéticos",
    "ficticia": True,
}

UNIDADES = {"UN-A": "Software", "UN-B": "Serviços"}

PRODUTOS = {
    "P-1": "SMA Analytics (licença)",
    "P-2": "SMA Ledger (licença)",
    "P-3": "Implantação",
    "P-4": "Suporte gerenciado",
}

CENTROS_CUSTO = {"CC-ADM": "Administrativo", "CC-COM": "Comercial", "CC-OPS": "Operações"}

CONTAS = ["C-3001 Pessoal", "C-3002 Marketing", "C-3003 Servicos", "C-3004 Logistica"]

PESSOAS = {  # usuário -> (nome fictício, cargo)
    "ana": ("Ana Lima", "analista"),
    "bruno": ("Bruno Souza", "analista"),
    "carla": ("Carla Mendes", "gerente"),
    "diego": ("Diego Rocha", "gerente"),
    "elisa": ("Elisa Prado", "diretor"),
}

LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" '
    'aria-label="SMA">'
    '<defs><clipPath id="sma-c"><rect x="2" y="2" width="60" height="60" rx="14"/></clipPath></defs>'
    '<g clip-path="url(#sma-c)"><rect x="2" y="2" width="60" height="60" fill="#1F4E79"/>'
    '<rect x="2" y="47" width="60" height="15" fill="#F2A900"/></g>'
    '<text x="32" y="38" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="22" '
    'font-weight="700" fill="#FFFFFF">SMA</text>'
    '</svg>'
)
