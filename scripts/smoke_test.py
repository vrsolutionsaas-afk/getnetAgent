"""Smoke test: dispara os cenarios do desafio contra a API rodando.

Pre-requisito: API de pe (docker compose up ou uvicorn) e base ja indexada.

Uso:
    python -m scripts.smoke_test
    python -m scripts.smoke_test http://localhost:8000
"""

import sys

import httpx

CENARIOS = [
    "What's the difference between the Get Clássica and the Get Smart?",
    "What's the weather forecast in Porto Alegre tomorrow?",
    "When will the money from yesterday's sales be deposited?",
    "Do I need a bank account to receive my sales via Pix?",
    "My card machine won't connect to the internet, what should I do?",
    "How does receivables advance (antecipação) work with Getnet?",
    "What's the euro exchange rate today?",
    "My card machine is showing a transaction decline error.",
    "How many installments can I split a sale into with the crediário?",
    "Can I sell through WhatsApp using the Payment Link?",
]

USER_ID = "cliente1988"


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    url = f"{base}/chat"

    with httpx.Client(timeout=60) as cliente:
        for i, mensagem in enumerate(CENARIOS, 1):
            print(f"\n{'=' * 70}\n[{i}] {mensagem}")
            try:
                resp = cliente.post(url, json={"message": mensagem, "user_id": USER_ID})
                resp.raise_for_status()
                dados = resp.json()
                print(f"  rota={dados['route']} | agente={dados['agent']} | "
                      f"escalado={dados['escalated']}")
                print(f"  trace={dados['trace']}")
                print(f"  resposta: {dados['response'][:300]}")
                if dados["sources"]:
                    print(f"  fontes: {dados['sources']}")
            except Exception as exc:  # noqa: BLE001
                print(f"  ERRO: {exc}")


if __name__ == "__main__":
    main()
