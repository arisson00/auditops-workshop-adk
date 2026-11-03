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
| [08. AlloyDB](labs/08-alloydb/) | O banco vetorial por dentro: trechos, vetores e busca por significado em SQL | 15 min |

Os labs 01 a 06 já vêm com o código pronto e comentado, na pasta `starter/`. Em cada um você **entende** o código, **testa** com o script `verificar.py` e **personaliza**: muda instruções, acrescenta campos, cria o seu próprio especialista, escreve a sua regra de custo e tenta enganar o agente. A pasta `solucao/` guarda a versão original, para comparar. O lab 07 publica o AuditOps completo, que está na raiz deste repositório, e o lab 08 abre o banco AlloyDB que ele usa.

No total são cerca de 1h45 de labs.

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
| `lab app` | Abre o AuditOps publicado no lab 07, mesmo quando a organização bloqueia acesso público |
| `lab alloydb` | Cria o banco AlloyDB em segundo plano, ou confere o que já existe; `lab alloydb senha` mostra a senha |
| `lab limpar` | Apaga o que o workshop criou no projeto, para não gerar custo |

> **Apareceu `nenhum projeto GCP selecionado`?** Rode `gcloud config set project <SEU_PROJECT_ID>` e repita o `source`. O `<SEU_PROJECT_ID>` é o ID do projeto (ex.: `meu-projeto-123456`), que aparece no seletor do topo do console.
>
> **Trocou de projeto ou de conta?** Rode `gcloud config set project <OUTRO_PROJECT_ID>`. O próximo `lab` já usa o projeto novo.
>
> **Já tinha clonado antes?** Rode `cd ~/auditops-workshop-adk && git pull && source workshop/ativar.sh`.

3. Dispare a criação do banco **AlloyDB**, que os labs 07 e 08 usam:

```bash
lab alloydb
```

Ele leva de 25 a 35 minutos para ficar pronto e roda em segundo plano: pode seguir com os labs enquanto isso. Para ver o andamento, rode `lab alloydb` de novo.

- Se a infra já criou o banco no seu projeto, o comando só confere que ele está pronto.
- O AlloyDB **cobra por hora enquanto existir**. No fim do workshop, rode `lab limpar`.

Depois, siga para o [Lab 01](labs/01-primeiro-agente/).
