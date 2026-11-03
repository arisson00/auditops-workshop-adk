#!/usr/bin/env bash
# =========================================================================================
# Script Replicável de Provisionamento do Google Cloud AlloyDB AI (pgvector + Vertex AI)
# Funciona em QUALQUER projeto GCP de cliente no Bootcamp (auto-detecta Project ID/Number)
# Uso: ./setup_alloydb.sh [PROJECT_ID] [REGION]
#
# Se o AlloyDB já existe (ex.: criado pela infra via Terraform), o script não recria nada: só confere
# e conecta o Cloud Run. Nomes diferentes dos padrões entram pelas mesmas variáveis do deploy_gcp.sh:
#   ALLOYDB_CLUSTER, ALLOYDB_INSTANCE, ALLOYDB_SECRET, VPC_NETWORK, VPC_SUBNET
# =========================================================================================
set -e

ACTIVE_GCLOUD_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
PROJECT_ID="${1:-${GOOGLE_CLOUD_PROJECT:-${ACTIVE_GCLOUD_PROJECT}}}"
if [ -z "$PROJECT_ID" ]; then
  echo "ERRO: nenhum projeto GCP definido. Rode: gcloud config set project <SEU_PROJECT_ID>"
  exit 1
fi
REGION="${2:-${GOOGLE_CLOUD_LOCATION:-us-central1}}"
CLUSTER_ID="${ALLOYDB_CLUSTER:-auditops-alloydb-cluster}"
INSTANCE_ID="${ALLOYDB_INSTANCE:-auditops-alloydb-primary}"
DB_SECRET="${ALLOYDB_SECRET:-auditops-alloydb-password}"
NETWORK="${VPC_NETWORK:-default}"
SUBNET="${VPC_SUBNET:-$NETWORK}"

# Auto-detecta o PROJECT_NUMBER do projeto do cliente
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

echo "=================================================================="
echo " Provisionando Google Cloud AlloyDB AI para o AuditOps Executive"
echo " Projeto  : $PROJECT_ID ($PROJECT_NUMBER)"
echo " Região   : $REGION"
echo " Cluster  : $CLUSTER_ID"
echo " Instância: $INSTANCE_ID"
echo "=================================================================="

gcloud config set project "$PROJECT_ID"

# 1. Habilita APIs do AlloyDB, Compute Engine e Service Networking
echo "-> Habilitando APIs do AlloyDB e Rede VPC..."
gcloud services enable \
  alloydb.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com

# 1.0 Se a instância já existe (criada antes ou pela infra), não recria nada: só conecta o Cloud Run.
#     O segredo precisa existir: uma senha nova não bateria com a do banco que já está lá
JA_EXISTE=false
if gcloud alloydb instances describe "$INSTANCE_ID" --cluster="$CLUSTER_ID" --region="$REGION" >/dev/null 2>&1; then
  JA_EXISTE=true
  if ! gcloud secrets describe "$DB_SECRET" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "ERRO: o AlloyDB [$CLUSTER_ID/$INSTANCE_ID] já existe, mas o segredo da senha [$DB_SECRET] não."
    echo "      Peça à infra o nome do segredo e rode: ALLOYDB_SECRET=<nome> ./setup_alloydb.sh"
    exit 1
  fi
  echo "-> AlloyDB [$CLUSTER_ID/$INSTANCE_ID] já existe: pulando a criação."
fi

if [ "$JA_EXISTE" = "false" ]; then
# 1.1 Senha do AlloyDB vem do Secret Manager; na primeira execução é gerada aleatoriamente
if ! gcloud secrets describe "$DB_SECRET" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "-> Gerando senha aleatória e criando secret [$DB_SECRET]..."
  openssl rand -base64 24 | tr -d '\n' | gcloud secrets create "$DB_SECRET" \
    --project="$PROJECT_ID" --replication-policy=automatic --data-file=-
fi
DB_PASSWORD=$(gcloud secrets versions access latest --secret="$DB_SECRET" --project="$PROJECT_ID")

# 2. A rede precisa existir. Muitos projetos de empresa são criados sem a rede "default"
if ! gcloud compute networks describe "$NETWORK" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "ERRO: a rede VPC [$NETWORK] não existe no projeto [$PROJECT_ID]."
  echo "      Peça à infra a rede usada no bootcamp e rode: VPC_NETWORK=<rede> VPC_SUBNET=<sub-rede> ./setup_alloydb.sh"
  echo "      Ou, num projeto de testes só seu, crie a rede padrão: gcloud compute networks create default --subnet-mode=auto"
  exit 1
fi

# 2.1 Configura Private Services Access (VPC Peering) na rede (obrigatório para AlloyDB)
echo "-> Verificando/Configurando VPC Peering (Private Services Access) na rede [$NETWORK]..."
if ! gcloud compute addresses describe google-managed-services-${NETWORK} --global >/dev/null 2>&1; then
  echo "   Criando faixa de IP interno [google-managed-services-${NETWORK}]..."
  gcloud compute addresses create google-managed-services-${NETWORK} \
    --global \
    --purpose=VPC_PEERING \
    --prefix-length=16 \
    --network="$NETWORK"
fi

echo "   Conectando VPC Peering com servicenetworking.googleapis.com..."
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-${NETWORK} \
  --network="$NETWORK" \
  --project="$PROJECT_ID" || true

# 3. Cria o Cluster do AlloyDB na VPC default (caso não exista)
if ! gcloud alloydb clusters describe "$CLUSTER_ID" --region="$REGION" >/dev/null 2>&1; then
  echo "-> Criando Cluster AlloyDB [$CLUSTER_ID]..."
  gcloud alloydb clusters create "$CLUSTER_ID" \
    --region="$REGION" \
    --password="$DB_PASSWORD" \
    --network="$NETWORK"
else
  echo "-> Cluster [$CLUSTER_ID] já existe."
fi

# 4. Concede permissão para a Service Account do AlloyDB chamar o Vertex AI (text-embedding-004 via SQL)
echo "-> Configurando integração IAM do AlloyDB com Vertex AI (google_ml_integration)..."
ALLOYDB_SA="service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${ALLOYDB_SA}" \
  --role="roles/aiplatform.user" \
  --condition=None \
  --quiet >/dev/null 2>&1 || true

# 5. Cria a Instância Primária do AlloyDB com suporte a google_ml_integration
if ! gcloud alloydb instances describe "$INSTANCE_ID" --cluster="$CLUSTER_ID" --region="$REGION" >/dev/null 2>&1; then
  echo "-> Criando Instância Primária [$INSTANCE_ID] (2 vCPUs)..."
  gcloud alloydb instances create "$INSTANCE_ID" \
    --cluster="$CLUSTER_ID" \
    --region="$REGION" \
    --instance-type=PRIMARY \
    --cpu-count=2 \
    --database-flags=google_ml_integration.enable_model_support=on
else
  echo "-> Instância [$INSTANCE_ID] já existe."
fi

fi  # fim da criação (JA_EXISTE=false)

# 6. Obtém o IP Privado da Instância AlloyDB
ALLOYDB_IP=$(gcloud alloydb instances describe "$INSTANCE_ID" --cluster="$CLUSTER_ID" --region="$REGION" --format="value(ipAddress)")

# 7. Se o serviço Cloud Run já existir, conecta automaticamente ao AlloyDB via Direct VPC Egress
if gcloud run services describe auditops-executive --region="$REGION" >/dev/null 2>&1; then
  echo "-> Conectando o serviço Cloud Run [auditops-executive] à VPC do AlloyDB ($ALLOYDB_IP)..."
  # O Cloud Run lê a senha do segredo: sem este acesso a nova revisão não sobe
  gcloud secrets add-iam-policy-binding "$DB_SECRET" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    --quiet >/dev/null
  gcloud run services update auditops-executive \
    --region="$REGION" \
    --network="$NETWORK" \
    --subnet="$SUBNET" \
    --vpc-egress=private-ranges-only \
    --update-env-vars="ALLOYDB_HOST=${ALLOYDB_IP}" \
    --update-secrets="ALLOYDB_PASSWORD=${DB_SECRET}:latest"
fi

echo "=================================================================="
echo " AlloyDB AI provisionado com sucesso!"
echo " IP Privado (ALLOYDB_HOST): $ALLOYDB_IP"
echo " O AuditOps cria as tabelas e carrega os playbooks sozinho ao conectar."
echo "=================================================================="
