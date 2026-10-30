#!/usr/bin/env bash
# =========================================================================================
# Remove tudo o que o AuditOps criou no projeto (Cloud Run, AlloyDB, segredo e imagens),
# para não deixar cobrança correndo depois do bootcamp. O AlloyDB é o item mais caro.
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
SERVICE_NAME="auditops-executive"
CLUSTER_ID="auditops-alloydb-cluster"
DB_SECRET="auditops-alloydb-password"

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
echo "  - imagens do build       repositório cloud-run-source-deploy"
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
gcloud artifacts repositories delete cloud-run-source-deploy --location "$REGION" --project "$PROJECT_ID" --quiet \
  && echo "✓ Imagens apagadas" || echo "- Repositório de imagens não encontrado"

echo "Limpeza concluída. Confira o faturamento em https://console.cloud.google.com/billing?project=$PROJECT_ID"
