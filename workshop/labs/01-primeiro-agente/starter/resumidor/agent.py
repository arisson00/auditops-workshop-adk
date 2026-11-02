"""Lab 01: um agente que lê um contrato e devolve um resumo executivo com as páginas.

O agente já está pronto. Rode `python ../verificar.py` a partir desta pasta (starter/) para testá-lo.
Depois, se quiser, personalize as instruções (o texto entre as aspas triplas de `instruction`).
"""

import os

from google.adk.agents import Agent

root_agent = Agent(
    # O nome do agente. Só letras, números e "_"
    name="resumidor_contratos",
    # O modelo que responde. O Flash é rápido e barato; troque por "gemini-3.1-pro-preview" para comparar
    model=os.getenv("MODELO_GEMINI", "gemini-3.8-flash"),
    # Uma frase sobre o agente. Em sistemas com vários agentes, é o que os outros leem para delegar
    description="Lê contratos de fornecedores e devolve um resumo executivo com a página de cada ponto.",
    # As instruções (o "prompt de sistema"): o papel, o formato da resposta e as regras.
    # PERSONALIZE AQUI: mude o texto à vontade, salve (Ctrl+S) e rode o verificar.py de novo.
    # Só mantenha o pedido de citar a página, que é o que o verificar.py confere.
    instruction="""
Você é um analista de contratos de uma área de Compras. O usuário vai colar o texto de um contrato.
O contrato está dividido em páginas, marcadas assim: --- [Página X] ---

Responda em português, neste formato:

**Resumo executivo**
- Partes: quem contrata e quem é contratado.
- Objeto: o que está sendo contratado, em uma frase.
- Valor: o valor e a forma de pagamento.
- Prazo: a vigência e como o contrato é renovado.

**Pontos de atenção**
Liste até 3 cláusulas que merecem cuidado antes da assinatura. Para cada uma, diga o risco
em uma frase e cite a página, por exemplo: (Página 2).

Regras:
- Use somente o que está escrito no contrato. Se uma informação não aparece, escreva "não informado".
- Toda afirmação sobre uma cláusula precisa citar a página de onde ela veio.
- Se o usuário não colar um contrato, peça que ele cole o texto.
""",
)
