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

## Passo 1: entrar no lab

```bash
lab 02
```

Desta vez o agente tem dois arquivos, e os dois já vêm prontos:

```
starter/extrator/
├── __init__.py
├── schemas.py   ← o formato da resposta: os campos do JSON
└── agent.py     ← o agente, que usa o schema
```

## Passo 2: conhecer o schema

Abra o arquivo no editor:

```bash
cloudshell edit extrator/schemas.py
```

O schema é uma classe Python que lista os campos do JSON. Cada linha segue o mesmo modelo:

```python
nome_do_campo: tipo = Field(description="o que o Gemini deve colocar aqui")
```

| Tipo | Exemplo no arquivo | O que garante |
|---|---|---|
| `str` | `titulo`, `objeto` | Um texto |
| `int` | `pagina`, `prazo_meses` | Um número, nunca "página dois" |
| `bool` | `renovacao_automatica` | `true` ou `false` |
| `Literal[...]` | `risco` | Só os valores listados: `alto`, `medio` ou `baixo` |
| `... \| None` | `valor_mensal`, `foro` | Pode vir vazio (`null`) quando o contrato não traz a informação |
| `list[Clausula]` | `clausulas` | Uma lista em que cada item segue a classe `Clausula` |

Repare nas descrições. O Gemini lê cada uma delas, e uma boa descrição vale tanto quanto uma linha de instrução.

## Passo 3: conhecer o agente

```bash
cloudshell edit extrator/agent.py
```

O agente é quase igual ao do Lab 01. As novidades são as duas últimas linhas, marcadas com `NOVO NESTE LAB`:

| Parâmetro | O que faz |
|---|---|
| `output_schema=ExtracaoContrato` | Obriga o Gemini a responder com um JSON nesse formato |
| `output_key="extracao"` | Guarda a resposta no estado da sessão com a chave `extracao`. No Lab 04, é por ali que um agente passa o resultado para o próximo. |

Repare também que as instruções ficaram curtas: **o que** extrair está no schema, campo a campo.

## Passo 4: testar o agente

No terminal, ainda na pasta do lab, rode:

```bash
python ../verificar.py
```

> Mudou de pasta ou abriu outro terminal? Rode `lab 02` antes.

Em uns 15 a 20 segundos, o script manda o [contrato de exemplo](contrato_exemplo.md) ao agente, lê o JSON em `state["extracao"]`, confere os campos e imprime as cláusulas ordenadas por risco:

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
lab web
```

Abra o link que o `lab web` mostra, escolha o app **extrator** e cole o contrato. A resposta agora chega como JSON. Clique nela e procure a aba de estado (**State**): a mesma resposta aparece guardada na chave `extracao`.

## Personalize o schema (opcional)

Aqui está a graça deste lab: **para extrair uma informação nova, basta acrescentar um campo no schema**. Não precisa mexer nas instruções.

1. No `extrator/schemas.py`, procure as linhas `# PERSONALIZE AQUI`.
2. Cole um dos campos abaixo logo depois delas, com 4 espaços no começo, alinhado aos outros campos.
3. Salve com `Ctrl+S` e rode `python ../verificar.py`. O campo novo aparece preenchido na saída.

Campos para o contrato inteiro (classe `ExtracaoContrato`):

| Para extrair… | Cole |
|---|---|
| A multa de rescisão | `multa_rescisao: str \| None = Field(description="Multa por rescisão antecipada, ou null se não houver")` |
| O índice de reajuste | `indice_reajuste: str \| None = Field(description="Índice e percentual de reajuste do preço, ex.: 'IPCA + 6%'")` |
| O aviso para não renovar | `aviso_previo_dias: int \| None = Field(description="Dias de antecedência para avisar que não quer renovar")` |
| Uma nota geral | `nota_risco: int = Field(description="Nota de 0 (sem risco) a 10 (risco máximo) para a CONTRATANTE")` |
| A recomendação | `recomendacao: Literal["ASSINAR", "ASSINAR COM AJUSTES", "NAO ASSINAR"] = Field(description="Recomendação para a diretoria")` |

Campos para cada cláusula (classe `Clausula`):

| Para extrair… | Cole |
|---|---|
| O que negociar | `sugestao_ajuste: str = Field(description="Como renegociar esta cláusula, em uma frase")` |
| A lei envolvida | `lei_relacionada: str \| None = Field(description="Lei brasileira relacionada, ex.: LGPD, Código Civil, ou null")` |
| Quem é favorecido | `favorece: Literal["contratante", "contratada", "equilibrada"] = Field(description="Qual parte a cláusula favorece")` |

Exemplo de saída com `sugestao_ajuste` e `multa_rescisao`:

```
  [alto ] p.3  Rescisão e Multa Desproporcional
           sugestao_ajuste: Limitar a multa a 10% do saldo remanescente.
Campos que você acrescentou:
  multa_rescisao: Todas as mensalidades restantes até o fim do contrato
```

Ideias para ir além:

- Invente um campo que a sua empresa precisa e escreva a descrição como se explicasse a um analista novo.
- Cole um texto que não é contrato (uma receita de bolo, por exemplo). O que o agente devolve? Acrescente `eh_contrato: bool` e veja o Gemini marcar `false`.
- Escreva uma descrição vaga (*"informação"*) e depois uma precisa. Compare o que volta.

Duas regras para o `verificar.py` continuar passando:

- **Não apague nem renomeie os campos que já existem.** O script confere vários deles.
- **Cuidado com o alinhamento:** os campos novos ficam com 4 espaços no começo, iguais aos outros.

Quer voltar ao original? Rode `git checkout extrator/`.

## Travou?

| O que aparece | O que fazer |
|---|---|
| `lab: command not found` | Prepare o workshop: veja o [README do workshop](../../README.md#antes-de-começar). |
| `✗ não achei a pasta extrator/` | Você saiu da pasta do lab. Rode `lab 02`. |
| `IndentationError` ou `SyntaxError` | Um campo novo ficou desalinhado ou com aspas faltando. Confira os 4 espaços no começo da linha, ou rode `git checkout extrator/` para voltar ao original. |
| `NameError: name 'Literal' is not defined` | O `from typing import Literal` no topo do `schemas.py` foi apagado. Coloque de volta. |
| `✗ TODO ... pendente` | Um dos campos originais foi apagado ou renomeado. Rode `git checkout extrator/` para voltar ao original. |
| `nada foi salvo em state["extracao"]` | O `output_key` foi alterado. Ele precisa ser exatamente `"extracao"`. |
| `prazo_meses deveria ser 24` ou parecido | O Gemini errou um campo. Rode de novo; se repetir, melhore a descrição do campo no schema. |
| Erros de `404`, `403` ou `429` | Veja a tabela do Lab 01. |

## Próximo lab

Até aqui o contrato inteiro vai junto na mensagem. Funciona com 3 páginas, mas não com 80. No **Lab 03**, o agente ganha uma **ferramenta de busca**: em vez de ler tudo, ele procura só os trechos que interessam e cita as páginas deles. Isso é RAG.
