# Lab 01: seu primeiro agente

**Tempo:** 10 a 15 minutos

**Ao final você terá** um agente Gemini que lê um contrato e devolve um resumo executivo, citando a página de cada ponto. Ele é a semente do AuditOps: nos próximos labs, este agente ganha saída estruturada, busca nas páginas e colegas especialistas.

## O que você vai aprender

| Conceito | Para que serve |
|---|---|
| `Agent` | É o agente: junta um modelo, instruções e (mais tarde) ferramentas. |
| `model` | Qual Gemini responde. O Flash é rápido e barato, ideal para triagem. |
| `instruction` | O "prompt de sistema": o papel, o formato da resposta e as regras do agente. |
| `description` | Uma frase sobre o agente. Em sistemas com vários agentes, é o que os outros leem para decidir a quem delegar. |
| `adk web` | Uma interface no navegador para conversar com o agente e ver cada chamada ao modelo. |

## Passo 1: entrar no lab

```bash
lab 01
```

O comando `lab` entra na pasta do lab, ativa o ambiente Python e cria o arquivo `resumidor/.env` apontando para o seu projeto GCP. O agente chama o Gemini pelo Vertex AI com a sua conta do Cloud Shell, sem chave de API.

> Aparece `lab: command not found`? Você ainda não preparou o workshop: veja o [README do workshop](../../README.md#antes-de-começar).

A pasta tem este formato, que é o que o ADK espera:

```
starter/
└── resumidor/          ← o nome da pasta é o nome do app no adk web
    ├── __init__.py     ← só importa o agent.py
    └── agent.py        ← define o agente (já vem pronto)
```

## Passo 2: conhecer o agente

Abra o arquivo no editor do Cloud Shell:

```bash
cloudshell edit resumidor/agent.py
```

> Se o comando não abrir nada, clique em **Abrir editor** no topo do Cloud Shell e navegue até `workshop/labs/01-primeiro-agente/starter/resumidor/agent.py`.

O agente já vem pronto. São só quatro peças:

| Peça | No arquivo | O que faz |
|---|---|---|
| `name` | `"resumidor_contratos"` | O nome do agente |
| `model` | `"gemini-3.8-flash"` | O Gemini que responde |
| `description` | `"Lê contratos de fornecedores..."` | Uma frase sobre o agente, para outros agentes saberem o que ele faz |
| `instruction` | O texto entre `"""` e `"""` | O "prompt de sistema": o papel, o formato da resposta e as regras |

Repare que as instruções são texto comum, em português. É assim que você "programa" o comportamento do agente.

## Passo 3: testar o agente

No terminal, ainda na pasta do lab, rode:

```bash
python ../verificar.py
```

> Mudou de pasta ou abriu outro terminal? Rode `lab 01` antes.

Em uns 15 a 20 segundos, o script:

1. confere se o agente está configurado: `✓ agente resumidor_contratos configurado com gemini-3.8-flash`;
2. manda o [contrato de exemplo](contrato_exemplo.md) para o Gemini e mostra o resumo que voltou;
3. confere se o resumo cita as páginas do contrato.

Deu certo quando a última linha é:

```
✓ a resposta cita as páginas 1, 2, 3. Lab 01 concluído!
```

Se aparecer uma linha com `✗`, ela diz o que fazer. Veja também a tabela [Travou?](#travou) no fim desta página.

## Passo 4: conversar com o agente no navegador

Ainda na pasta do lab, rode:

```bash
lab web
```

O `lab web` sobe a interface do ADK (`adk web`) já liberada para a Visualização da Web do Cloud Shell.

> Na primeira vez, o ADK pergunta `Enable telemetry? [Y/n]`. Responda `n` ou `y` e aperte Enter; a escolha não muda nada no lab.

1. Abra o link que o `lab web` mostra entre as duas linhas, que termina em `cloudshell.dev`. Se não aparecer link, clique no topo do Cloud Shell em **Visualização da Web** > **Visualizar na porta 8080**.

   **Não clique no `http://127.0.0.1:8080`** que o ADK escreve logo abaixo: esse é o endereço da máquina do Cloud Shell, e no seu navegador ele não abre nada.
2. No canto superior esquerdo, escolha o app **resumidor**.
3. Abra o `contrato_exemplo.md`, copie todo o texto, cole no chat e envie.
4. Clique na resposta e abra a aba **Events** (ou **Trace**). Ali aparece exatamente o que foi enviado ao Gemini, incluindo as instruções, e quanto tempo levou.

Para parar o servidor, use `Ctrl+C` no terminal.

## Personalize as instruções (opcional)

O jeito mais rápido de entender um agente é mudar as instruções e ver a resposta mudar.

1. No `resumidor/agent.py`, edite o texto entre `"""` e `"""` do `instruction`.
2. Salve com `Ctrl+S`.
3. Rode `python ../verificar.py` de novo. Se o `adk web` estiver aberto, basta mandar o contrato outra vez: ele recarrega o agente sozinho.

Ideias prontas para colar no fim das instruções, antes das `"""` finais:

| Para… | Acrescente |
|---|---|
| Classificar o risco | `- Classifique cada ponto de atenção como risco ALTO, MÉDIO ou BAIXO.` |
| Escrever para a diretoria | `- Escreva para a diretoria: frases curtas, sem juridiquês, no máximo 10 linhas.` |
| Sugerir o que negociar | `- Para cada ponto de atenção, sugira em uma frase como renegociá-lo.` |
| Responder em outro idioma | `- Responda em espanhol.` |
| Dar uma recomendação final | `- Termine com uma recomendação: ASSINAR, ASSINAR COM AJUSTES ou NÃO ASSINAR.` |

Também dá para trocar o papel inteiro, por exemplo: *"Você é o advogado da empresa contratada"*. Compare como a mesma cláusula vira risco ou vantagem conforme o ponto de vista.

Duas regras para o `verificar.py` continuar passando:

- **Mantenha o pedido de citar a página**, por exemplo `(Página 2)`. É o que o script confere.
- **Não apague as `"""`** do começo e do fim do texto.

Para outros testes:

- Pergunte algo que não está no contrato (*"Qual é o CNPJ da contratada?"*). Ele responde "não informado" ou inventa? Se inventar, reforce a regra nas instruções.
- Troque o modelo para `"gemini-3.1-pro-preview"` e compare a resposta e o tempo.

Quer voltar ao original? Rode `git checkout resumidor/agent.py`.

## Travou?

| O que aparece | O que fazer |
|---|---|
| `lab: command not found` | Prepare o workshop: veja o [README do workshop](../../README.md#antes-de-começar). |
| `✗ não achei a pasta resumidor/` | Você saiu da pasta do lab. Rode `lab 01`. |
| `SyntaxError` | Faltou ou sobrou uma `"""` nas instruções. Rode `git checkout resumidor/agent.py` para voltar ao original. |
| `as instruções não falam em página` | A sua personalização tirou o pedido de citar a página. Acrescente de volta, ex.: *"cite a página, ex.: (Página 2)"*. |
| `a resposta deveria citar pelo menos 2 páginas` | O Gemini não citou as páginas desta vez. Reforce isso nas instruções e rode de novo. |
| `404` ou `Publisher Model ... not found` | Rode `lab 01` de novo: ele refaz o `.env` com `GOOGLE_CLOUD_LOCATION=global`, o endpoint onde os modelos Gemini 3.x existem. |
| `403` / `PERMISSION_DENIED` | A API Vertex AI não está ativa ou a sua conta não tem o papel *Vertex AI User*. Rode `gcloud services enable aiplatform.googleapis.com`. |
| `429` / `RESOURCE_EXHAUSTED` | Cota momentânea. Espere 1 minuto e tente de novo. |
| A página do `adk web` fica em branco, e o terminal mostra `403 Forbidden` nos arquivos `.js` | Você rodou `adk web` direto. Pare com `Ctrl+C` e use `lab web`, que libera o endereço da Visualização da Web. |
| O navegador não abre nada em `http://127.0.0.1:8080` | Esse endereço só existe dentro do Cloud Shell. Use o link `...cloudshell.dev` que o `lab web` mostra, ou **Visualização da Web** > **Visualizar na porta 8080**. |
| `address already in use` | Um `adk web` antigo ainda está aberto (em outra aba ou pausado com `Ctrl+Z`). Rode `lab web`: ele encerra o antigo sozinho. Se avisar que **outro programa** usa a porta, veja qual com `lsof -i :8080`. |

## Próximo lab

No **Lab 02**, o agente deixa de responder em texto livre e passa a devolver um JSON com campos fixos (partes, valor, prazo, cláusulas e páginas). É isso que permite que outros agentes e a interface usem a resposta.
