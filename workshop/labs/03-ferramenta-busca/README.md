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

## Passo 1: entrar na pasta e configurar o projeto

```bash
cd labs/03-ferramenta-busca/starter
cat > assistente/.env <<EOF
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
GOOGLE_CLOUD_LOCATION=global
EOF
```

```
starter/assistente/
├── __init__.py
├── busca.py    ← a busca nas páginas (pronta, só leia)
└── agent.py    ← a ferramenta e o agente (TODOs 1 a 4)
```

O contrato é o [contrato_technova.md](contrato_technova.md), o mesmo que aparece na demo do AuditOps.

## Passo 2: entender a busca (2 minutos de leitura)

Abra `assistente/busca.py`. Ele faz duas coisas:

1. **Indexa:** corta o contrato em trechos, um por cláusula, e cada trecho guarda a sua página.
2. **Busca:** dá a cada trecho uma nota pelas palavras da consulta que ele contém e devolve os melhores.

É a versão mais simples de busca. Repare em um limite dela: buscar `"cancelar contrato"` não encontra nada, porque o contrato fala em "rescisão". Guarde isso para o passo 5.

## Passo 3: transformar a busca numa ferramenta

Abra `assistente/agent.py`. A função `buscar_no_contrato` é a ferramenta.

1. **TODO 1, a docstring:** escreva o que a ferramenta faz, quando usar e o que é o argumento `consulta`, com um exemplo. Escreva para o Gemini, como faria para um colega novo.
2. **TODO 2, o retorno:** devolva um dicionário com os trechos, cada um com página e texto. A linha pronta está no comentário.

## Passo 4: entregar a ferramenta ao agente e escrever as regras

3. **TODO 3:** adicione `tools=[buscar_no_contrato]` ao `Agent`.
4. **TODO 4:** troque o TODO das instruções pelas regras. O comentário lista o que elas precisam ter. A mais importante é a última: se não achar, responder exatamente *"Não consta no contrato."*

## Passo 5: verificar

```bash
python ../verificar.py
```

O script faz 3 perguntas e mostra **cada chamada que o agente fez à ferramenta**:

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

## Passo 6: ver no navegador

```bash
adk web --port 8080
```

Abra pela **Visualização da Web** (porta 8080) e escolha o app **assistente**. Faça perguntas, como *"Os dados podem sair do Brasil?"* e *"Existe limite de indenização?"*. Na visualização dos eventos, cada chamada a `buscar_no_contrato` aparece com a consulta enviada e os trechos que voltaram.

## Experimente (se sobrar tempo)

- Apague a docstring da ferramenta (deixe só `"""Busca."""`) e faça as mesmas perguntas. O agente continua usando bem a ferramenta?
- Mude `quantidade=3` para `quantidade=1` no `agent.py`. As respostas pioram?
- Pergunte algo que exige juntar duas cláusulas: *"Se a plataforma ficar fora do ar, podemos cancelar sem multa?"* (resposta nas páginas 2 e 4).

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
| `✗ TODO ... pendente` | Falta aquele TODO no `agent.py`. |
| `o agente respondeu sem usar a ferramenta` | Confira o TODO 3 e reforce nas regras: "Antes de responder, use a ferramenta buscar_no_contrato". |
| `a resposta deveria citar a Página ...` | Reforce nas regras que toda informação cita a página. Rode de novo. |
| `UserWarning: [EXPERIMENTAL] feature ... enabled` no `adk web` | Aviso interno do ADK. Pode ignorar. |
| Erros de `404`, `403` ou `429` | Veja a tabela do Lab 01. |
| Ainda não funciona | A resposta está em `../solucao/assistente/`. |

## Próximo lab

Agora você tem as peças: um extrator (Lab 02) e um assistente com busca (Lab 03). No **Lab 04**, vários agentes especialistas trabalham juntos: um extrai, outro confere as políticas de compliance, outro avalia o risco jurídico, e o resultado de um passa para o próximo pelo estado da sessão.
