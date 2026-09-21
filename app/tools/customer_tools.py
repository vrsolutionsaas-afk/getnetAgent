"""Ferramentas do Customer Support Agent.

Cada ferramenta retorna FATOS estruturados (dict), nunca texto final para o
usuario. O agente compoe a resposta em linguagem natural a partir desses fatos.
Sao 3 tools sobre a base simulada de clientes (o desafio exige no minimo 2).
"""

from app.data.mock_users import buscar_cliente


def consultar_liquidacao_vendas(user_id: str) -> dict:
    """Consulta quando e quanto o cliente vai receber das vendas recentes.

    Responde perguntas como: "quando cai o dinheiro da venda de ontem?".
    """
    cliente = buscar_cliente(user_id)
    if not cliente:
        return {"encontrado": False, "motivo": "cliente_nao_encontrado"}

    liq = cliente["liquidacao"]
    return {
        "encontrado": True,
        "nome": cliente["nome"],
        "plano_recebimento": cliente["plano_recebimento"],
        "vendas_de": liq["vendas_de"],
        "valor_bruto": liq["valor_bruto"],
        "valor_liquido": liq["valor_liquido"],
        "data_prevista_deposito": liq["data_prevista_deposito"],
        "status": liq["status"],
        "conta_bancaria": cliente["conta_bancaria"],
    }


def consultar_status_maquininha(user_id: str) -> dict:
    """Consulta o status/conectividade da maquininha do cliente.

    Responde perguntas como: "minha maquininha nao conecta na internet".
    """
    cliente = buscar_cliente(user_id)
    if not cliente:
        return {"encontrado": False, "motivo": "cliente_nao_encontrado"}

    maq = cliente["maquininha"]
    return {
        "encontrado": True,
        "nome": cliente["nome"],
        "modelo": maq["modelo"],
        "numero_serie": maq["numero_serie"],
        "status_conexao": maq["status_conexao"],
        "ultima_conexao": maq["ultima_conexao"],
        "diagnostico": maq["diagnostico"],
    }


def consultar_antecipacao(user_id: str) -> dict:
    """Consulta a disponibilidade de antecipacao de recebiveis do cliente.

    Responde perguntas como: "posso antecipar minhas vendas?".
    """
    cliente = buscar_cliente(user_id)
    if not cliente:
        return {"encontrado": False, "motivo": "cliente_nao_encontrado"}

    ant = cliente["antecipacao"]
    return {
        "encontrado": True,
        "nome": cliente["nome"],
        "disponivel": ant["disponivel"],
        "valor_disponivel": ant["valor_disponivel"],
        "taxa_mensal": ant["taxa_mensal"],
        "valor_liquido_antecipado": ant["valor_liquido_antecipado"],
    }
