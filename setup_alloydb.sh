#!/usr/bin/env bash
# =========================================================================================
# Script Replicável de Provisionamento do Google Cloud AlloyDB AI (pgvector + Vertex AI)
# Funciona em QUALQUER projeto GCP de cliente no Bootcamp (auto-detecta Project ID/Number)
# Uso: ./setup_alloydb.sh [PROJECT_ID] [REGION]
# =========================================================================================
set -e

ACTIVE_GCLOUD_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
PROJECT_ID="${1:-${GOOGLE_CLOUD_PROJECT:-${ACTIVE_GCLOUD_PROJECT}}}"
if [ -z "$PROJECT_ID" ]; then
  echo "ERRO: nenhum projeto GCP definido. Rode: gcloud config set project <SEU_PROJECT_ID>"
  exit 1
fi
REGION="${2:-${GOOGLE_CLOUD_LOCATION:-us-central1}}"
CLUSTER_ID="auditops-alloydb-cluster"
INSTANCE_ID="auditops-alloydb-primary"
DB_SECRET="auditops-alloydb-password"
NETWORK="default"

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

# 1.1 Senha do AlloyDB vem do Secret Manager; na primeira execução é gerada aleatoriamente
if ! gcloud secrets describe "$DB_SECRET" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "-> Gerando senha aleatória e criando secret [$DB_SECRET]..."
  openssl rand -base64 24 | tr -d '\n' | gcloud secrets create "$DB_SECRET" \
    --project="$PROJECT_ID" --replication-policy=automatic --data-file=-
fi
DB_PASSWORD=$(gcloud secrets versions access latest --secret="$DB_SECRET" --project="$PROJECT_ID")

# 2. Configura Private Services Access (VPC Peering) na rede default (obrigatório para AlloyDB)
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
    --subnet="$NETWORK" \
    --vpc-egress=private-ranges-only \
    --update-env-vars="ALLOYDB_HOST=${ALLOYDB_IP}" \
    --update-secrets="ALLOYDB_PASSWORD=${DB_SECRET}:latest"
fi

echo "=================================================================="
echo " AlloyDB AI provisionado com sucesso!"
echo " IP Privado (ALLOYDB_HOST): $ALLOYDB_IP"
echo " O AuditOps cria as tabelas e carrega os playbooks sozinho ao conectar."
echo "=================================================================="
