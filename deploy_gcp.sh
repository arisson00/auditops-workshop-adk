#!/usr/bin/env bash
# =========================================================================================
# Deploy do AuditOps Executive no Cloud Run, pensado para o projeto GCP de cada participante.
# Funciona com ou sem AlloyDB: sem ele, a busca roda em memória; com ele (./setup_alloydb.sh),
# este script conecta o serviço à instância automaticamente.
#
# Uso (no Cloud Shell, dentro da pasta do projeto):
#   ./deploy_gcp.sh [PROJECT_ID] [REGION]
# =========================================================================================
set -euo pipefail

PROJECT_ID="${1:-${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}}"
REGION="${2:-${GOOGLE_CLOUD_LOCATION:-us-central1}}"
# Nomes dos recursos: se a infra criou com outros nomes (ex.: via Terraform), basta exportar a variável
SERVICE_NAME="${SERVICE_NAME:-auditops-executive}"
CLUSTER_ID="${ALLOYDB_CLUSTER:-auditops-alloydb-cluster}"
INSTANCE_ID="${ALLOYDB_INSTANCE:-auditops-alloydb-primary}"
DB_SECRET="${ALLOYDB_SECRET:-auditops-alloydb-password}"
NETWORK="${VPC_NETWORK:-default}"
SUBNET="${VPC_SUBNET:-$NETWORK}"
RUN_SA="${RUN_SERVICE_ACCOUNT:-}"
MODEL_FAST="${MODEL_TIER_FAST:-gemini-3.8-flash}"
MODEL_PRO="${MODEL_TIER_REASONING:-gemini-3.1-pro-preview}"

if [ -z "$PROJECT_ID" ]; then
  echo "ERRO: nenhum projeto GCP definido."
  echo "      Rode: gcloud config set project <SEU_PROJECT_ID>   (ou ./deploy_gcp.sh <SEU_PROJECT_ID>)"
  exit 1
fi

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null || true)
if [ -z "$PROJECT_NUMBER" ]; then
  echo "ERRO: não encontrei o projeto [$PROJECT_ID] ou você não tem acesso a ele."
  echo "      Confira o ID em https://console.cloud.google.com/home/dashboard e a conta em: gcloud auth list"
  exit 1
fi

echo "=================================================================="
echo " Deploy do AuditOps Executive"
echo " Projeto : $PROJECT_ID ($PROJECT_NUMBER)"
echo " Região  : $REGION"
echo " Modelos : $MODEL_FAST (triagem) e $MODEL_PRO (parecer)"
echo "=================================================================="

gcloud config set project "$PROJECT_ID" >/dev/null 2>&1
gcloud auth application-default set-quota-project "$PROJECT_ID" >/dev/null 2>&1 || true

# 1. Faturamento: sem ele nenhuma API abaixo pode ser ativada
BILLING=$(gcloud billing projects describe "$PROJECT_ID" --format="value(billingEnabled)" 2>/dev/null || echo "")
if [ "$BILLING" = "False" ]; then
  echo "ERRO: o projeto [$PROJECT_ID] está sem conta de faturamento."
  echo "      Vincule uma em https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
  exit 1
fi

# 2. APIs
echo "-> [1/5] Ativando APIs (pode levar 1-2 minutos na primeira vez)..."
# Sem permissão para ativar APIs (ambiente preparado pela infra via Terraform), segue em frente
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  || echo "   Aviso: não consegui ativar as APIs (sem permissão?). Seguindo: elas devem ter sido ativadas pela infra."

# 3. Permissões da conta de serviço padrão (usada pelo build e pelo Cloud Run)
# O build (gcloud run deploy --source) roda com a conta padrão do Compute; o Cloud Run roda com ela
# ou com a conta criada pela infra (RUN_SERVICE_ACCOUNT)
BUILD_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
COMPUTE_SA="${RUN_SA:-$BUILD_SA}"
echo "-> [2/5] Dando permissões às contas de serviço (build: $BUILD_SA, execução: $COMPUTE_SA)..."
IAM_WARNED=false
grant() {
  if ! gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:$1" --role="$2" --condition=None --quiet >/dev/null 2>&1; then
    if [ "$IAM_WARNED" = "false" ]; then
      echo "   Aviso: sem permissão para alterar IAM. Seguindo: os papéis devem ter sido dados pela infra."
      IAM_WARNED=true
    fi
  fi
}
for ROLE in "roles/storage.objectAdmin" "roles/artifactregistry.writer" "roles/logging.logWriter" "roles/cloudbuild.builds.builder"; do
  grant "$BUILD_SA" "$ROLE"
done
for ROLE in "roles/logging.logWriter" "roles/alloydb.client" "roles/aiplatform.user"; do
  grant "$COMPUTE_SA" "$ROLE"
done

# 4. Confere se o projeto acessa os modelos Gemini; sem isso a aplicação só roda em modo demonstração
echo "-> [3/5] Testando acesso aos modelos Gemini..."
TOKEN=$(gcloud auth print-access-token)
GEMINI_OK=true
for MODEL in "$MODEL_FAST" "$MODEL_PRO"; do
  CODE="000"
  for _ in 1 2 3; do
    # Logo após ativar a API o Vertex pode responder 403 por alguns segundos
    CODE=$(curl -s -o /tmp/auditops_gemini_check.json -w "%{http_code}" -X POST \
      -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
      "https://aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/global/publishers/google/models/${MODEL}:generateContent" \
      -d '{"contents":[{"role":"user","parts":[{"text":"Responda apenas: ok"}]}],"generationConfig":{"maxOutputTokens":256}}' || true)
    CODE="${CODE:-000}"
    [ "$CODE" = "200" ] && break
    sleep 10
  done
  case "$CODE" in
    200) echo "   ✓ $MODEL respondeu" ;;
    404) echo "   ✗ $MODEL não está disponível neste projeto"; GEMINI_OK=false ;;
    429) echo "   ✗ $MODEL sem cota neste projeto (429)"; GEMINI_OK=false ;;
    403) echo "   ✗ sem permissão para $MODEL (403): confira se a API Vertex AI está ativa e se sua conta tem o papel Vertex AI User"; GEMINI_OK=false ;;
    *)   echo "   ✗ $MODEL respondeu HTTP $CODE: $(head -c 200 /tmp/auditops_gemini_check.json 2>/dev/null)"; GEMINI_OK=false ;;
  esac
done
rm -f /tmp/auditops_gemini_check.json
if [ "$GEMINI_OK" != "true" ]; then
  echo "   ATENÇÃO: o deploy segue, mas as auditorias vão rodar em modo demonstração (selo 'Modo demonstração' na tela)."
  echo "            Para trocar os modelos: MODEL_TIER_FAST=<modelo> MODEL_TIER_REASONING=<modelo> ./deploy_gcp.sh"
fi

# 5. AlloyDB é opcional: só conecta se a instância e o segredo da senha já existirem
ALLOYDB_IP=$(gcloud alloydb instances describe "$INSTANCE_ID" --cluster="$CLUSTER_ID" --region="$REGION" \
  --project="$PROJECT_ID" --format="value(ipAddress)" 2>/dev/null || true)
EXTRA_FLAGS=()
if [ -n "$ALLOYDB_IP" ] && gcloud secrets describe "$DB_SECRET" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "-> [4/5] AlloyDB encontrado em $ALLOYDB_IP: o serviço vai se conectar pela VPC."
  gcloud secrets add-iam-policy-binding "$DB_SECRET" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    --quiet >/dev/null 2>&1 \
    || echo "   Aviso: não consegui dar acesso ao segredo $DB_SECRET; a infra precisa conceder secretAccessor a $COMPUTE_SA."
  EXTRA_FLAGS=(--network="$NETWORK" --subnet="$SUBNET" --vpc-egress=private-ranges-only
               --set-secrets="ALLOYDB_PASSWORD=${DB_SECRET}:latest")
else
  echo "-> [4/5] Sem AlloyDB neste projeto: a busca vai rodar em memória (rode ./setup_alloydb.sh depois, se quiser)."
  ALLOYDB_IP=""
fi

# 6. Build e deploy. Logo após conceder as permissões o build pode falhar por propagação de IAM:
#    nesse caso espera 1 minuto e tenta de novo
echo "-> [5/5] Fazendo build e deploy no Cloud Run (3-5 minutos)..."
deploy() {
  gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --timeout 600 \
    --max-instances 2 \
    --concurrency 20 \
    --session-affinity \
    --service-account "$COMPUTE_SA" \
    --quiet \
    ${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"} \
    --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_PROJECT_NUMBER=${PROJECT_NUMBER},GOOGLE_CLOUD_LOCATION=${REGION},GEMINI_LOCATION=global,AUDITOPS_STRICT_LIVE=false,AUDITOPS_MAX_CONCURRENT_AUDITS=3,AUDITOPS_AUDITS_PER_HOUR=20,AUDITOPS_CHATS_PER_HOUR=60,EMBEDDING_MODEL=text-embedding-004,ALLOYDB_CLUSTER=${CLUSTER_ID},ALLOYDB_INSTANCE=${INSTANCE_ID},ALLOYDB_HOST=${ALLOYDB_IP},MODEL_TIER_FAST=${MODEL_FAST},MODEL_TIER_STANDARD=${MODEL_FAST},MODEL_TIER_REASONING=${MODEL_PRO}"
}
if ! deploy; then
  echo "   O deploy falhou; esperando 60s (propagação de permissões) e tentando de novo..."
  sleep 60
  deploy
fi

URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format="value(status.url)")
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$URL/" || true)

echo "=================================================================="
if [ "$HTTP" = "200" ]; then
  echo " ✓ AuditOps no ar: $URL"
else
  echo " ✓ Deploy concluído, mas o acesso público está bloqueado (HTTP $HTTP)."
  echo "   Provável política da organização que impede serviços abertos. Para abrir pelo Cloud Shell:"
  echo "     gcloud run services proxy $SERVICE_NAME --region $REGION --port 8080"
  echo "   e depois clique em 'Visualização da Web' > 'Visualizar na porta 8080'."
fi
[ "$GEMINI_OK" = "true" ] || echo " ! Modelos Gemini indisponíveis: auditorias em modo demonstração (veja as mensagens acima)."
echo "=================================================================="
