# Lab 03: uma ferramenta de busca (RAG)

**Tempo:** 15 minutos

**Ao final você terá** um assistente que responde perguntas sobre um contrato de 5 páginas. Ele não recebe o contrato inteiro: decide sozinho o que buscar, lê só os trechos que interessam e cita a página de cada informação. Quando o assunto não está no contrato, ele diz isso em vez de inventar.

Nos labs 01 e 02 o contrato inteiro ia junto na mensagem. Isso funciona com 3 páginas, mas não com 80, nem com uma carteira de 200 contratos. A saída é dar ao agente uma **ferramenta de busca** e deixar que ele a use. Esse padrão se chama **RAG** (*Retrieval-Augmented Generation*: geração apoiada em busca).

## O que você vai aprender

| Conceito | Para que serve |
|---|---|
| Ferramenta (*tool*) | Uma função Python comum que o agente pode chamar. O ADK transforma a função em algo que o Gemini entende. |
| Docstring | O texto entre `"""` no começo da função. O Gemini lê esse texto para decidir **quando** chamar a ferramenta e **o que** passar. |
| `tools=[...]` | A lista de ferramentas que o agente pode usar. |
| RAG | Buscar primeiro, responder depois, só com o que foi encontrado, e citar a fonte. |

## Passo 1: entrar no lab

```bash
lab 03
```

```
starter/assistente/
├── __init__.py
├── busca.py    ← a busca nas páginas do contrato
└── agent.py    ← a ferramenta e o agente
```

Os dois arquivos já vêm prontos. O contrato é o [contrato_technova.md](contrato_technova.md), o mesmo que aparece na demo do AuditOps.

## Passo 2: entender a busca (2 minutos de leitura)

```bash
cloudshell edit assistente/busca.py
```

O `busca.py` faz duas coisas:

1. **Indexa:** corta o contrato em trechos, um por cláusula, e cada trecho guarda a sua página.
2. **Busca:** dá a cada trecho uma nota pelas palavras da consulta que ele contém e devolve os melhores.

É a versão mais simples de busca. Repare num limite dela: buscar `"cancelar contrato"` não encontra nada, porque o contrato fala em "rescisão". Guarde isso para o passo 4.

## Passo 3: conhecer a ferramenta e o agente

```bash
cloudshell edit assistente/agent.py
```

| Parte | O que faz |
|---|---|
| `def buscar_no_contrato(consulta)` | A **ferramenta**: uma função Python comum, que chama a busca e devolve os trechos com a página |
| A docstring (texto entre `"""` logo abaixo do `def`) | O "manual" da ferramenta. O Gemini lê esse texto para decidir **quando** chamá-la e **o que** passar em `consulta`. |
| `tools=[buscar_no_contrato]` | Entrega a ferramenta ao agente. Está marcada com `NOVO NESTE LAB`. |
| As regras nas instruções | Buscar antes de responder, citar a página e, se não achar, dizer *"Não consta no contrato."* |

Repare que ninguém escreveu "chame a busca com tal palavra". O Gemini decide sozinho o que buscar e quantas vezes.

## Passo 4: testar o agente

No terminal, ainda na pasta do lab, rode:

```bash
python ../verificar.py
```

> Mudou de pasta ou abriu outro terminal? Rode `lab 03` antes.

Em uns 30 segundos, o script faz 3 perguntas e mostra **cada chamada que o agente fez à ferramenta**:

```
? Podemos cancelar o contrato antes do prazo? Quanto custa?
  → buscar_no_contrato(consulta="rescisão cancelamento multa")
  Sim, é possível rescindir o contrato antes do prazo (Página 4). ... multa compensatória
  de 50% do valor total das mensalidades restantes (Página 4).

? Qual é o telefone do suporte técnico?
  → buscar_no_contrato(consulta="suporte técnico telefone contato")
  → buscar_no_contrato(consulta="suporte SLA atendimento canal helpdesk")
  → buscar_no_contrato(consulta="telefone contato comunicacao notificacao email")
  Não consta no contrato.
```

Repare em duas coisas:

- **Na 2ª pergunta**, a busca por palavras não acharia "cancelar". Quem resolveu foi o Gemini: ele mesmo trocou por "rescisão" na consulta.
- **Na 3ª pergunta**, ele buscou várias vezes com outras palavras, não achou e disse isso. Ninguém programou esse laço: o agente decide quantas vezes chamar a ferramenta.

As consultas e o número de buscas mudam a cada execução.

## Passo 5: pergunte o que quiser

Passe a sua pergunta entre aspas, e o script responde só ela, mostrando as buscas:

```bash
python ../verificar.py "Os dados podem sair do Brasil?"
```

Dá para mandar várias de uma vez:

```bash
python ../verificar.py "Existe limite de indenização?" "Quem paga a arbitragem?" "Qual é o SLA?"
```

Boas perguntas para testar:

| Pergunta | O que observar |
|---|---|
| *"Se a plataforma ficar fora do ar, podemos cancelar sem multa?"* | Precisa juntar duas cláusulas (páginas 2 e 4). O agente faz mais de uma busca? |
| *"Quanto vamos pagar no total em 3 anos?"* | O agente faz a conta a partir do valor mensal? |
| *"Esse contrato é bom para nós?"* | Pergunta de opinião: ele busca os riscos ou responde genérico? |
| *"Qual é a cor do logotipo da TechNova?"* | Fora do contrato: ele diz "Não consta" ou inventa? |

Prefere o navegador? Rode `lab web`, abra o link que aparece e escolha o app **assistente**. Cada chamada a `buscar_no_contrato` aparece nos eventos, com a consulta e os trechos que voltaram.

## Personalize (opcional)

No `assistente/agent.py`, procure as linhas `PERSONALIZE`. Salve com `Ctrl+S` e rode `python ../verificar.py` de novo depois de cada mudança.

| Experimento | O que mudar | O que observar |
|---|---|---|
| A docstring importa? | Troque a docstring inteira por `"""Busca."""` | O agente continua escolhendo boas palavras para a consulta? |
| Quantos trechos? | Mude `quantidade=3` para `1` ou `5` | Com 1, as respostas pioram? Com 5, ficam mais longas? |
| Sem sinônimos | Apague a frase *"tente de novo com outras palavras-chave"* | A pergunta sobre cancelar ainda funciona? |
| Mais formal | Acrescente às regras: *"Responda como um parecer jurídico, em tom formal."* | O tom muda sem mudar as páginas citadas? |
| Resposta em tópicos | Acrescente: *"Responda em tópicos, um por informação, cada um com a página."* | Fica mais fácil de ler? |

Duas regras para o `verificar.py` continuar passando:

- **Mantenha a frase** *"Não consta no contrato."* nas regras. O script confere essa resposta exata.
- **Mantenha o pedido de citar a página.**

Quer voltar ao original? Rode `git checkout assistente/`.

## Como isso funciona no AuditOps de verdade

| Aqui no lab | No AuditOps em produção |
|---|---|
| Nota por palavras em comum | Nota por **significado**: cada trecho vira um vetor (*embedding*) com o modelo `text-embedding-004`, e "cancelar" fica perto de "rescisão" |
| Trechos numa lista em memória | Trechos e vetores no **AlloyDB** com **pgvector**, com índice HNSW para buscar rápido em milhares de trechos |
| Um contrato | A carteira toda, mais as políticas internas de compliance |

O agente e a ferramenta são os mesmos. Só muda o que está dentro de `buscar()`.

## Travou?

| O que aparece | O que fazer |
|---|---|
| `lab: command not found` | Prepare o workshop: veja o [README do workshop](../../README.md#antes-de-começar). |
| `✗ não achei a pasta assistente/` | Você saiu da pasta do lab. Rode `lab 03`. |
| `✗ TODO 1 pendente: escreva a docstring` | A docstring foi apagada. Escreva ao menos uma frase sobre o que a ferramenta faz, entre `"""` logo abaixo do `def`. |
| `o agente respondeu sem usar a ferramenta` | Reforce nas regras: *"Antes de responder, use a ferramenta buscar_no_contrato"*. |
| `a resposta deveria citar a Página ...` | Reforce nas regras que toda informação cita a página. Rode de novo. |
| `IndentationError` ou `SyntaxError` | Alguma linha ficou desalinhada ou com aspas faltando. Rode `git checkout assistente/` para voltar ao original. |
| `UserWarning: [EXPERIMENTAL] feature ... enabled` | Aviso interno do ADK. Pode ignorar. |
| Erros de `404`, `403` ou `429` | Veja a tabela do Lab 01. |

## Próximo lab

Agora você tem as peças: um extrator (Lab 02) e um assistente com busca (Lab 03). No **Lab 04**, vários agentes especialistas trabalham juntos: um extrai, outro confere as políticas de compliance, outro avalia o risco jurídico, e o resultado de um passa para o próximo pelo estado da sessão.
