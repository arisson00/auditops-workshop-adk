#!/usr/bin/env bash
# =========================================================================================
# Remove tudo o que o AuditOps criou no projeto (Cloud Run, AlloyDB, segredo e imagem do app),
# para não deixar cobrança correndo depois do bootcamp. O AlloyDB é o item mais caro.
# Só apaga a imagem do AuditOps: o repositório cloud-run-source-deploy é o padrão do Google Cloud
# para qualquer deploy com --source e pode guardar imagens de outros serviços do projeto.
#
# Uso: ./cleanup_gcp.sh [--so-app] [PROJECT_ID] [REGION]      (pede confirmação antes de apagar)
#   --so-app  apaga só o Cloud Run e as imagens; use quando o AlloyDB e o segredo foram criados
#             pela infra (Terraform), que cuida de apagá-los com terraform destroy
# =========================================================================================
set -uo pipefail

ONLY_APP=false
if [ "${1:-}" = "--so-app" ]; then
  ONLY_APP=true
  shift
fi

PROJECT_ID="${1:-${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}}"
REGION="${2:-${GOOGLE_CLOUD_LOCATION:-us-central1}}"
SERVICE_NAME="${SERVICE_NAME:-auditops-executive}"
CLUSTER_ID="${ALLOYDB_CLUSTER:-auditops-alloydb-cluster}"
DB_SECRET="${ALLOYDB_SECRET:-auditops-alloydb-password}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}"

if [ -z "$PROJECT_ID" ]; then
  echo "ERRO: nenhum projeto GCP definido. Rode: gcloud config set project <SEU_PROJECT_ID>"
  exit 1
fi

echo "Vou apagar do projeto [$PROJECT_ID], região [$REGION]:"
echo "  - serviço Cloud Run      $SERVICE_NAME"
if [ "$ONLY_APP" = "false" ]; then
  echo "  - cluster AlloyDB        $CLUSTER_ID (com a instância e todos os dados)"
  echo "  - segredo                $DB_SECRET"
fi
echo "  - imagem do app          $IMAGE (o repositório e as outras imagens ficam)"
echo "  - processador de OCR     auditops-ocr (Document AI), se existir"
read -r -p "Digite o ID do projeto para confirmar: " CONFIRM
if [ "$CONFIRM" != "$PROJECT_ID" ]; then
  echo "Cancelado: nada foi apagado."
  exit 1
fi

gcloud run services delete "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID" --quiet \
  && echo "✓ Cloud Run apagado" || echo "- Cloud Run não encontrado"
if [ "$ONLY_APP" = "false" ]; then
  gcloud alloydb clusters delete "$CLUSTER_ID" --region "$REGION" --project "$PROJECT_ID" --force --quiet \
    && echo "✓ AlloyDB apagado" || echo "- AlloyDB não encontrado"
  gcloud secrets delete "$DB_SECRET" --project "$PROJECT_ID" --quiet \
    && echo "✓ Segredo apagado" || echo "- Segredo não encontrado"
fi
gcloud artifacts docker images delete "$IMAGE" --delete-tags --project "$PROJECT_ID" --quiet \
  && echo "✓ Imagem do app apagada" || echo "- Imagem do app não encontrada"

# Só apaga o processador criado pelo deploy_gcp.sh; um processador da infra tem outro nome e fica
OCR_API="https://us-documentai.googleapis.com/v1/projects/${PROJECT_ID}/locations/us/processors"
TOKEN=$(gcloud auth print-access-token 2>/dev/null || true)
OCR_PROCESSOR=$(curl -s -H "Authorization: Bearer ${TOKEN}" "$OCR_API" | python3 -c \
  "import json,sys; ps=json.load(sys.stdin).get('processors',[]); print(next((p['name'] for p in ps if p.get('displayName')=='auditops-ocr'),''))" \
  2>/dev/null || true)
if [ -n "$OCR_PROCESSOR" ] && curl -sf -X DELETE -H "Authorization: Bearer ${TOKEN}" \
    "https://us-documentai.googleapis.com/v1/${OCR_PROCESSOR}" >/dev/null; then
  echo "✓ Processador de OCR apagado"
else
  echo "- Processador de OCR não encontrado"
fi

echo "Limpeza concluída. Confira o faturamento em https://console.cloud.google.com/billing?project=$PROJECT_ID"
