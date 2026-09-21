"""Base de dados simulada de clientes Getnet para as ferramentas de suporte.

Em producao isto seria substituido por consultas a APIs internas / banco de dados.
Os dados abaixo sao ficticios e servem para demonstrar as tools do Support Agent.
"""

from datetime import date, timedelta

_hoje = date.today()


def _iso(dias_atras: int) -> str:
    return (_hoje - timedelta(days=dias_atras)).isoformat()


def _iso_futuro(dias_frente: int) -> str:
    return (_hoje + timedelta(days=dias_frente)).isoformat()


# Chave = user_id
CLIENTES: dict[str, dict] = {
    "cliente1988": {
        "nome": "Maria Souza",
        "plano_recebimento": "1 dia util (D+1)",
        "conta_bancaria": "Banco Santander - Ag 1234 / CC 56789-0",
        "maquininha": {
            "modelo": "Get Smart",
            "numero_serie": "GS-2026-0091",
            "status_conexao": "offline",
            "ultima_conexao": _iso(1),
            "diagnostico": "Sem sinal de dados. Wi-Fi configurado mas sem internet.",
        },
        "vendas_recentes": [
            {"data": _iso(1), "valor": 1250.00, "bandeira": "Visa credito", "parcelas": 1},
            {"data": _iso(1), "valor": 340.90, "bandeira": "Mastercard debito", "parcelas": 1},
            {"data": _iso(2), "valor": 890.00, "bandeira": "Elo credito", "parcelas": 3},
        ],
        "liquidacao": {
            "vendas_de": _iso(1),
            "valor_bruto": 1590.90,
            "valor_liquido": 1544.68,
            "data_prevista_deposito": _iso_futuro(0),
            "status": "agendado",
        },
        "antecipacao": {
            "disponivel": True,
            "valor_disponivel": 1544.68,
            "taxa_mensal": 1.99,
            "valor_liquido_antecipado": 1503.20,
        },
    },
    "cliente2025": {
        "nome": "Joao Pereira",
        "plano_recebimento": "30 dias (D+30)",
        "conta_bancaria": "Banco do Brasil - Ag 4321 / CC 09876-5",
        "maquininha": {
            "modelo": "Get Clássica",
            "numero_serie": "GC-2026-0412",
            "status_conexao": "online",
            "ultima_conexao": _iso(0),
            "diagnostico": "Operando normalmente.",
        },
        "vendas_recentes": [
            {"data": _iso(0), "valor": 59.90, "bandeira": "Pix", "parcelas": 1},
        ],
        "liquidacao": {
            "vendas_de": _iso(0),
            "valor_bruto": 59.90,
            "valor_liquido": 59.90,
            "data_prevista_deposito": _iso_futuro(0),
            "status": "concluido",
        },
        "antecipacao": {
            "disponivel": False,
            "valor_disponivel": 0.0,
            "taxa_mensal": 1.99,
            "valor_liquido_antecipado": 0.0,
        },
    },
}


def buscar_cliente(user_id: str) -> dict | None:
    """Retorna o registro do cliente ou None se nao existir."""
    return CLIENTES.get(user_id)
