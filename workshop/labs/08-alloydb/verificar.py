"""Confere o Lab 08: o AuditOps publicado está usando o AlloyDB?

Uso, de dentro da pasta do lab (lab 08):
    python verificar.py            (descobre a URL do app pelo gcloud)
    python verificar.py <URL>

1. Confere se o app está conectado ao AlloyDB.
2. Audita o contrato da VeloNet, para o banco ter trechos de contrato e uma linha de telemetria
   frescos para você explorar no AlloyDB Studio.
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
SERVICO = "auditops-executive"
REGIAO = "us-central1"


def falhar(mensagem: str) -> None:
    print(f"✗ {mensagem}")
    sys.exit(1)


def gcloud(*args: str) -> str:
    try:
        return subprocess.run(["gcloud", *args], capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else gcloud(
    "run", "services", "describe", SERVICO, "--region", REGIAO, "--format", "value(status.url)")
if not URL:
    falhar(f"não achei o serviço {SERVICO}. Faça o Lab 07 antes: lab 07 e depois ./deploy_gcp.sh")

# Se a organização bloqueia acesso público, a chamada vai autenticada com o seu login
CABECALHOS = {"Content-Type": "application/json"}


def chamar(caminho: str, corpo: dict | None = None, tempo_limite: int = 30) -> dict:
    dados = json.dumps(corpo).encode() if corpo is not None else None
    pedido = urllib.request.Request(URL + caminho, data=dados, headers=CABECALHOS)
    with urllib.request.urlopen(pedido, timeout=tempo_limite) as resposta:
        return json.loads(resposta.read())


try:
    meta = chamar("/api/samples")
except urllib.error.HTTPError as erro:
    if erro.code not in (401, 403):
        falhar(f"{URL} respondeu HTTP {erro.code}.")
    token = gcloud("auth", "print-identity-token")
    if not token:
        falhar(f"{URL} exige login e não consegui gerar um token.")
    CABECALHOS["Authorization"] = f"Bearer {token}"
    meta = chamar("/api/samples")
except urllib.error.URLError as erro:
    falhar(f"não consegui abrir {URL}: {erro.reason}")

# 1. O app está conectado ao AlloyDB?
banco = meta["vector_db_meta"]
if not banco.get("live_pg_connection"):
    print(f"  status do app: {banco.get('status_summary', '')}")
    falhar("o app não está conectado ao AlloyDB.\n"
           "  1. Rode `lab alloydb` e confira se ele está pronto.\n"
           "  2. Se estiver, publique o app de novo para ele achar o banco: lab 07 e depois ./deploy_gcp.sh")
print(f"✓ o app está conectado ao AlloyDB ({banco['alloydb_instance']})")
print(f"  {banco.get('indexed_kb_chunks', 0)} trechos de políticas indexados, "
      f"vetores de {banco.get('embedding_dimensions', 768)} dimensões ({banco.get('embedding_model', '')})")

# 2. Uma auditoria para o banco ter dados frescos
print("… auditando o contrato da VeloNet (cerca de 30 segundos)")
inicio = time.monotonic()
try:
    relatorio = chamar("/api/audit", {
        "contract_text": (RAIZ / "samples" / "contrato_telecom_sdwan.md").read_text(encoding="utf-8"),
        "contract_name": "VeloNet (lab 08)",
    }, tempo_limite=300)
except urllib.error.HTTPError as erro:
    falhar(f"a auditoria falhou com HTTP {erro.code}: {erro.read()[:300]!r}")
print(f"✓ auditoria gravada no banco em {time.monotonic() - inicio:.0f}s "
      f"(nota {relatorio['compliance']['compliance_score']}, risco {relatorio['legal_review']['overall_risk_level']})")
print("\nAgora abra o AlloyDB Studio e rode as consultas do passo 3 do README.")
print("A senha do usuário postgres aparece com:  lab alloydb senha")
