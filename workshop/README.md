# Workshop AuditOps: construa um auditor de contratos com agentes Gemini

Neste workshop você constrói, passo a passo, o AuditOps: um sistema de agentes que lê contratos de fornecedores, encontra as cláusulas de risco e cita a página de cada uma. Ele usa o **Google ADK** (Agent Development Kit) e os modelos **Gemini** no Vertex AI.

## Labs

| Lab | Você constrói | Tempo |
|---|---|---|
| [01. Primeiro agente](labs/01-primeiro-agente/) | Um agente que resume um contrato e cita as páginas | 10-15 min |
| [02. Saída estruturada](labs/02-saida-estruturada/) | O extrator de cláusulas devolvendo JSON | 15 min |
| [03. Ferramenta de busca](labs/03-ferramenta-busca/) | A busca nas páginas do contrato (RAG) | 15 min |
| [04. Vários agentes](labs/04-varios-agentes/) | Compliance e risco trabalhando juntos | 15 min |
| [05. Cascata Flash → Pro](labs/05-cascata-flash-pro/) | O modelo Pro só quando há risco | 10-15 min |
| [06. Guardrails](labs/06-guardrails/) | Bloqueio de tentativas de manipular o agente | 10-15 min |
| [07. Deploy](labs/07-deploy-cloud-run/) | O AuditOps completo publicado no Cloud Run | 15 min |

Os labs 01 e 02 já vêm com o agente pronto, para você testar e personalizar. Os labs 03 a 06 têm uma pasta `starter/` com lacunas marcadas `TODO` para você completar. Todos têm uma pasta `solucao/` e um script `verificar.py` que confere o seu trabalho. O lab 07 publica o AuditOps completo, que está na raiz deste repositório.

No total são cerca de 90 minutos de labs.

## Antes de começar

Você precisa de um projeto Google Cloud com faturamento ativo. Tudo roda no **Cloud Shell**, sem instalar nada no seu computador.

1. Abra https://console.cloud.google.com, escolha o seu projeto no seletor do topo e clique em **Ativar o Cloud Shell** (`>_`).
2. No terminal, cole as duas linhas:

```bash
git clone https://github.com/arisson00/auditops-workshop-adk.git
source auditops-workshop-adk/workshop/ativar.sh
```

Na primeira vez, o `ativar.sh` leva de 1 a 2 minutos: instala o Google ADK e ativa a API do Vertex AI no seu projeto. No fim aparece:

```
✓ workshop pronto no projeto <seu-projeto>. Para começar: lab 01
```

A partir daí, cada lab começa com um único comando, que funciona de qualquer pasta e mesmo depois de o Cloud Shell reiniciar:

| Comando | O que faz |
|---|---|
| `lab 01` | Entra no lab 01, ativa o ambiente e configura o seu projeto GCP |
| `lab 01 solucao` | O mesmo, na pasta da solução |
| `lab 07` | Vai para a raiz do repositório, para o deploy |
| `lab web` | Abre a interface do ADK no navegador, para o lab da pasta atual |

> **Apareceu `nenhum projeto GCP selecionado`?** Rode `gcloud config set project <SEU_PROJECT_ID>` e repita o `source`. O `<SEU_PROJECT_ID>` é o ID do projeto (ex.: `meu-projeto-123456`), que aparece no seletor do topo do console.
>
> **Trocou de projeto ou de conta?** Rode `gcloud config set project <OUTRO_PROJECT_ID>`. O próximo `lab` já usa o projeto novo.
>
> **Já tinha clonado antes?** Rode `cd ~/auditops-workshop-adk && git pull && source workshop/ativar.sh`.

Depois, siga para o [Lab 01](labs/01-primeiro-agente/).
