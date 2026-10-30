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

Os labs 01 a 06 têm uma pasta `starter/` com lacunas marcadas `TODO`, uma pasta `solucao/` e um script `verificar.py` que confere o seu trabalho. O lab 07 publica o AuditOps completo, que está na raiz deste repositório.

No total são cerca de 90 minutos de labs.

## Antes de começar

Você precisa de um projeto Google Cloud com faturamento ativo. Tudo roda no **Cloud Shell**, sem instalar nada no seu computador.

1. Abra https://console.cloud.google.com, escolha o seu projeto e clique em **Ativar o Cloud Shell** (`>_`).
2. No terminal:

```bash
gcloud config set project <SEU_PROJECT_ID>
gcloud services enable aiplatform.googleapis.com
git clone https://github.com/arisson00/auditops-workshop-adk.git ~/auditops-workshop
cd ~/auditops-workshop/workshop
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> Se o Cloud Shell reiniciar, rode de novo `cd ~/auditops-workshop/workshop && source .venv/bin/activate`.

Depois, siga para o [Lab 01](labs/01-primeiro-agente/).
