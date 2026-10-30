# Lab 02: saída estruturada

**Tempo:** 15 minutos

**Ao final você terá** um agente extrator que devolve um JSON com campos fixos: partes, valor, prazo, foro e uma lista de cláusulas, cada uma com página e nível de risco.

No Lab 01 o agente respondia em texto livre. Texto é ótimo para uma pessoa ler, mas difícil para um programa usar: não dá para ordenar as cláusulas por risco nem passar o valor do contrato para outro agente com segurança. Com saída estruturada, a resposta vira dados.

## O que você vai aprender

| Conceito | Para que serve |
|---|---|
| Schema Pydantic | Uma classe Python que descreve o formato da resposta: os campos, os tipos e uma descrição de cada um. |
| `output_schema` | Obriga o Gemini a responder com um JSON nesse formato. As descrições dos campos funcionam como instruções. |
| `Literal` | Limita um campo a valores fixos, ex.: risco só pode ser `alto`, `medio` ou `baixo`. |
| `output_key` | Guarda a resposta no **estado da sessão**. É por ali que, no Lab 04, um agente passa o resultado para o próximo. |

## Passo 1: entrar na pasta e configurar o projeto

```bash
cd labs/02-saida-estruturada/starter
cat > extrator/.env <<EOF
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
GOOGLE_CLOUD_LOCATION=global
EOF
```

Desta vez o agente tem dois arquivos:

```
starter/extrator/
├── __init__.py
├── schemas.py   ← o formato da resposta (TODOs 1 e 2)
└── agent.py     ← o agente (TODOs 3 e 4)
```

## Passo 2: completar o schema

Abra `extrator/schemas.py`. A classe `Clausula` já tem `titulo` e `resumo`. Siga o modelo deles e adicione:

1. **TODO 1:** o campo `pagina`, do tipo `int`. Na descrição, diga que a página vem do marcador `--- [Página X] ---`.
2. **TODO 2:** o campo `risco`, do tipo `Literal["alto", "medio", "baixo"]`.

> Capriche nas descrições. O Gemini lê cada uma delas, e uma boa descrição vale tanto quanto uma linha de instrução.

## Passo 3: ligar o schema ao agente

Abra `extrator/agent.py` e adicione dois parâmetros ao `Agent`, no lugar dos TODOs:

3. **TODO 3:** `output_schema=ExtracaoContrato`
4. **TODO 4:** `output_key="extracao"`

## Passo 4: verificar

```bash
python ../verificar.py
```

O script manda o contrato de exemplo ao agente, lê o JSON em `state["extracao"]`, confere os campos com o gabarito e imprime as cláusulas ordenadas por risco:

```
Cláusulas, da mais arriscada para a menos:
  [alto ] p.2  Renovação Automática
  [alto ] p.3  Rescisão e Multa Desproporcional
  [alto ] p.3  Uso de Dados sem Anonimização
  [medio] p.1  Reajuste de Preço
  ...
✓ 3 cláusula(s) de risco alto. Lab 02 concluído!
```

Os títulos e a quantidade de cláusulas mudam um pouco a cada execução. O formato é sempre o mesmo, e é isso que importa.

Repare nas últimas linhas do `verificar.py`: ordenar e contar as cláusulas é Python comum. Isso só é possível porque a resposta é um JSON com formato garantido.

## Passo 5: ver no navegador

```bash
adk web --port 8080
```

Abra pela **Visualização da Web** (porta 8080), escolha o app **extrator** e cole o contrato. A resposta agora chega como JSON. Clique nela e procure a aba de estado (**State**): a mesma resposta aparece guardada na chave `extracao`.

## Experimente (se sobrar tempo)

- Adicione na classe `ExtracaoContrato` um campo `multa_rescisao: str | None` e rode de novo. Você não mexeu nas instruções, e mesmo assim o Gemini preenche o campo novo.
- Adicione na `Clausula` um campo `sugestao_ajuste: str` com a descrição *"Como renegociar esta cláusula, em uma frase"*.
- Cole um texto que não é contrato (uma receita de bolo, por exemplo). O que o agente devolve? Como o schema poderia sinalizar isso? Dica: um campo `eh_contrato: bool`.

## Travou?

| O que aparece | O que fazer |
|---|---|
| `✗ TODO ... pendente` | Falta aquele TODO. A mensagem diz o arquivo. |
| `NameError: name 'Literal' is not defined` | O `from typing import Literal` no topo do `schemas.py` foi apagado. Coloque de volta. |
| `nada foi salvo em state["extracao"]` | O `output_key` está com outro nome. Precisa ser exatamente `"extracao"`. |
| `prazo_meses deveria ser 24` ou parecido | O Gemini errou um campo. Rode de novo; se repetir, melhore a descrição do campo no schema. |
| Erros de `404`, `403` ou `429` | Veja a tabela do Lab 01. |
| Ainda não funciona | A resposta está em `../solucao/extrator/`. |

## Próximo lab

Até aqui o contrato inteiro vai junto na mensagem. Funciona com 3 páginas, mas não com 80. No **Lab 03**, o agente ganha uma **ferramenta de busca**: em vez de ler tudo, ele procura só os trechos que interessam e cita as páginas deles. Isso é RAG.
