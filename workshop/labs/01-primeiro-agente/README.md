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

## Passo 1: entrar na pasta do lab

No Cloud Shell, dentro do repositório:

```bash
cd labs/01-primeiro-agente/starter
```

A pasta tem este formato, que é o que o ADK espera:

```
starter/
└── resumidor/          ← o nome da pasta é o nome do app no adk web
    ├── __init__.py     ← só importa o agent.py
    └── agent.py        ← define o root_agent (é aqui que você trabalha)
```

## Passo 2: apontar para o seu projeto GCP

O agente chama o Gemini pelo Vertex AI, com a sua conta do Cloud Shell. Não é preciso chave de API.

```bash
cat > resumidor/.env <<EOF
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
GOOGLE_CLOUD_LOCATION=global
EOF
```

> `GOOGLE_CLOUD_LOCATION=global` é obrigatório: os modelos Gemini 3.x só existem no endpoint global.

## Passo 3: preencher os TODOs

Abra `resumidor/agent.py` no editor do Cloud Shell (botão **Abrir editor**) e preencha:

1. **TODO 1, o modelo:** `"gemini-3.8-flash"`.
2. **TODO 2, a descrição:** uma frase, por exemplo: *"Lê contratos de fornecedores e devolve um resumo executivo com a página de cada ponto."*
3. **TODO 3, as instruções:** o comentário no arquivo lista o que elas precisam ter. Escreva com as suas palavras.

Dica para o TODO 3: escreva como se fosse orientar um analista novo da sua equipe. Diga o que ele vai receber, o formato que você quer de volta e o que ele não pode fazer.

## Passo 4: verificar

```bash
python ../verificar.py
```

O script confere os TODOs e manda o [contrato de exemplo](contrato_exemplo.md) ao seu agente. Se tudo der certo, ele mostra o resumo e termina com:

```
✓ a resposta cita as páginas 1, 2, 3. Lab 01 concluído!
```

## Passo 5: conversar com o agente no navegador

```bash
adk web --port 8080
```

1. No Cloud Shell, clique em **Visualização da Web** > **Visualizar na porta 8080**.
2. No canto superior esquerdo, escolha o app **resumidor**.
3. Cole o conteúdo de `contrato_exemplo.md` no chat e envie.
4. Clique na resposta e abra a aba **Events** (ou **Trace**). Ali aparece exatamente o que foi enviado ao Gemini, incluindo as suas instruções, e quanto tempo levou.

Para parar o servidor, use `Ctrl+C` no terminal.

## Experimente (se sobrar tempo)

Mude as instruções, salve o arquivo e mande o contrato de novo. O `adk web` recarrega o agente sozinho.

- Peça para classificar cada ponto de atenção como **alto**, **médio** ou **baixo** risco.
- Peça a resposta em espanhol ou em inglês.
- Faça uma pergunta que não tem resposta no contrato (*"Qual é o CNPJ da contratada?"*). Ele responde "não informado" ou inventa? Se inventar, reforce a regra nas instruções.
- Troque o modelo para `gemini-3.1-pro-preview` e compare a resposta e o tempo.

## Travou?

| O que aparece | O que fazer |
|---|---|
| `✗ não achei a pasta resumidor/` | Você não está dentro de `starter/`. Rode `cd labs/01-primeiro-agente/starter`. |
| `✗ TODO ... pendente` | Falta preencher aquele TODO no `agent.py`. |
| `404` ou `Publisher Model ... not found` | Confira se o `.env` tem `GOOGLE_CLOUD_LOCATION=global`. |
| `403` / `PERMISSION_DENIED` | A API Vertex AI não está ativa ou sua conta não tem o papel *Vertex AI User*. Rode `gcloud services enable aiplatform.googleapis.com`. |
| `429` / `RESOURCE_EXHAUSTED` | Cota momentânea. Espere 1 minuto e tente de novo. |
| Ainda não funciona | A resposta completa está em `../solucao/resumidor/agent.py`. Rode `cd ../solucao` e siga a partir do passo 2. |

## Próximo lab

No **Lab 02**, o agente deixa de responder em texto livre e passa a devolver um JSON com campos fixos (partes, valor, prazo, cláusulas e páginas). É isso que permite que outros agentes e a interface usem a resposta.
