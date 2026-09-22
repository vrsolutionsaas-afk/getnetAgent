"""Base de conhecimento curada dos produtos e servicos da Getnet.

Motivo: o site oficial (getnet.com.br) e uma SPA renderizada em JavaScript com
redirecionamentos de tracking, o que impede a extracao de conteudo util por
scraping estatico (httpx/BeautifulSoup) — todas as URLs caem numa home generica.

Esta base curada, escrita a partir de informacoes publicas dos produtos Getnet,
e a fonte principal do RAG e cobre os cenarios do desafio. O scraper do site
(ingest.py) permanece disponivel como fonte complementar.

Cada item vira um ou mais chunks no pgvector. O campo 'source' aponta para a
pagina oficial correspondente (usado como citacao na resposta).
"""

DOCUMENTOS_GETNET: list[dict] = [
    {
        "titulo": "Maquininhas Getnet: Get Clássica e Get Smart",
        "source": "https://www.getnet.com.br/maquininhas/",
        "conteudo": (
            "A Getnet oferece diferentes maquininhas de cartao para o seu negocio. "
            "A Get Clássica e a maquininha tradicional: pratica e funcional, aceita "
            "cartoes de credito, debito e voucher, alem de Pix, e envia o comprovante "
            "de forma digital. E ideal para quem busca uma solucao simples e economica "
            "para receber pagamentos. "
            "A Get Smart e a maquininha inteligente (smart POS): possui tela sensivel "
            "ao toque maior, sistema Android e permite instalar aplicativos, alem de "
            "aceitar credito, debito, voucher e Pix. E indicada para quem quer mais "
            "recursos, gestao pelo proprio aparelho e uma experiencia mais completa no "
            "ponto de venda. "
            "Principais diferencas: a Get Clássica foca no essencial (mais simples e "
            "economica), enquanto a Get Smart oferece tela touch ampla, Android e apps. "
            "Ambas aceitam as principais bandeiras, Pix e conexao via Wi-Fi ou chip."
        ),
    },
    {
        "titulo": "Conexao da maquininha (Wi-Fi e chip)",
        "source": "https://www.getnet.com.br/maquininhas/",
        "conteudo": (
            "As maquininhas Getnet conectam-se a internet por Wi-Fi ou por chip de dados. "
            "Se a maquininha nao conecta a internet, verifique: 1) se o Wi-Fi esta ativo "
            "e a senha foi digitada corretamente; 2) se o sinal do local e estavel; "
            "3) reinicie a maquininha; 4) se usa chip, confirme se ha cobertura de dados "
            "no local; 5) aproxime-se do roteador. Persistindo o problema, acione o "
            "suporte Getnet para diagnostico do aparelho."
        ),
    },
    {
        "titulo": "Erro de transacao recusada / negada",
        "source": "https://www.getnet.com.br/perguntas-frequentes/",
        "conteudo": (
            "Quando a maquininha exibe erro de transacao recusada ou negada, a causa "
            "costuma estar no cartao ou no banco emissor, nao na maquininha. Oriente o "
            "cliente a: conferir limite e saldo; tentar outra forma de pagamento "
            "(credito, debito, Pix); verificar se o cartao esta desbloqueado; e contatar "
            "o banco emissor. Se a recusa ocorrer com varios cartoes, verifique a conexao "
            "da maquininha e tente novamente."
        ),
    },
    {
        "titulo": "Receber por Pix com a Getnet",
        "source": "https://www.getnet.com.br/receba-por-pix/",
        "conteudo": (
            "Com a Getnet voce pode receber vendas por Pix diretamente na maquininha ou "
            "pelo link de pagamento. Nao e necessario ter conta em um banco especifico: "
            "o valor das vendas por Pix cai na conta que voce cadastrou para recebimento "
            "na Getnet. O recebimento via Pix costuma ser rapido, caindo na conta "
            "cadastrada. Voce nao precisa abrir conta em um banco novo apenas para "
            "receber por Pix — usa a conta bancaria informada no seu cadastro."
        ),
    },
    {
        "titulo": "Prazos de recebimento das vendas (liquidacao)",
        "source": "https://www.getnet.com.br/",
        "conteudo": (
            "O prazo para o dinheiro das vendas cair na conta depende do plano de "
            "recebimento contratado. Nos planos mais rapidos, as vendas no credito podem "
            "cair em 1 dia util (D+1); em outros planos, o prazo padrao do credito e de "
            "30 dias (D+30). Vendas no debito e por Pix costumam cair mais rapido. Para "
            "saber exatamente quando o valor de uma venda especifica sera depositado, "
            "consulte o extrato/painel Getnet ou o atendimento, informando a data da venda."
        ),
    },
    {
        "titulo": "Antecipacao de recebiveis",
        "source": "https://www.getnet.com.br/antecipacao-de-recebiveis/",
        "conteudo": (
            "A antecipacao de recebiveis permite receber antes o valor das vendas que "
            "cairiam no futuro (por exemplo, vendas parceladas ou no plano D+30). Em vez "
            "de esperar o prazo normal, voce adianta os valores e recebe na conta "
            "cadastrada, com desconto de uma taxa de antecipacao proporcional ao prazo "
            "antecipado. E util para melhorar o fluxo de caixa. A disponibilidade e o "
            "valor liquido dependem das vendas a receber e da taxa vigente."
        ),
    },
    {
        "titulo": "Crediario e parcelamento de vendas",
        "source": "https://www.getnet.com.br/",
        "conteudo": (
            "Com a Getnet e possivel parcelar as vendas no cartao de credito. O numero "
            "maximo de parcelas depende do seu plano/contrato e das regras das bandeiras, "
            "podendo chegar a varias parcelas (comumente ate 12x). Existe o parcelamento "
            "comum (o lojista recebe conforme o plano) e modalidades de crediario. "
            "Para saber o limite exato de parcelas do seu estabelecimento, consulte suas "
            "condicoes contratadas na Getnet."
        ),
    },
    {
        "titulo": "Link de pagamento e vendas pelo WhatsApp",
        "source": "https://www.getnet.com.br/link-de-pagamento/",
        "conteudo": (
            "O Link de Pagamento da Getnet permite vender a distancia sem maquininha: "
            "voce gera um link de cobranca e envia ao cliente por WhatsApp, e-mail ou "
            "redes sociais. O cliente paga com cartao de credito, debito ou Pix pelo "
            "proprio link, de forma segura. E ideal para vendas pelo WhatsApp, redes "
            "sociais e e-commerce. Sim, e possivel vender pelo WhatsApp usando o Link de "
            "Pagamento: basta enviar o link ao cliente."
        ),
    },
]
