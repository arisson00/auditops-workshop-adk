"""Confere o Lab 07: testa o AuditOps publicado no Cloud Run.

Uso, da raiz do repositório:
    python workshop/labs/07-deploy-cloud-run/verificar.py            (descobre a URL pelo gcloud)
    python workshop/labs/07-deploy-cloud-run/verificar.py <URL>      (ex.: http://localhost:8080 com o proxy)

Audita dois contratos pela API do serviço e compara com o que você construiu no Lab 05:
o contrato limpo fica no Flash, o contrato com desvios escala para o Pro.
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
    falhar(f"não achei o serviço {SERVICO} em {REGIAO}. O ./deploy_gcp.sh terminou com sucesso?")

# Se a organização bloqueia acesso público, a chamada vai autenticada com a sua conta
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
        falhar(f"{URL} exige login e não consegui gerar um token. Use o proxy (passo 3 do README).")
    CABECALHOS["Authorization"] = f"Bearer {token}"
    meta = chamar("/api/samples")
except urllib.error.URLError as erro:
    falhar(f"não consegui abrir {URL}: {erro.reason}")
print(f"✓ AuditOps no ar em {URL}")
print(f"  modelos: {meta['models']['flash_tier']} (triagem) e {meta['models']['pro_tier']} (parecer)")
banco = meta["vector_db_meta"]
print(f"  busca  : {'AlloyDB (' + banco['alloydb_instance'] + ')' if banco.get('live_pg_connection') else 'índice em memória'}")

CASOS = [
    ("VeloNet (limpo)", "contrato_telecom_sdwan.md"),
    ("TechNova (com desvios)", "contrato_saas_enterprise.md"),
]
linhas = []
for nome, arquivo in CASOS:
    print(f"… auditando {nome} (de 20 segundos a 2 minutos)")
    inicio = time.monotonic()
    try:
        r = chamar("/api/audit", {"contract_text": (RAIZ / "samples" / arquivo).read_text(encoding="utf-8"),
                                  "contract_name": nome}, tempo_limite=300)
    except urllib.error.HTTPError as erro:
        falhar(f"a auditoria de {nome} falhou com HTTP {erro.code}: {erro.read()[:300]!r}")
    linhas.append((nome, r, time.monotonic() - inicio))

print("-" * 86)
print(f"{'Contrato':24} {'Modo':10} {'Nota':>4}  {'Risco':9} {'Parecer no Pro?':16} {'Tempo':>6}  {'Custo est.':>10}")
for nome, r, tempo in linhas:
    f = r["finops"]
    print(f"{nome:24} {r['execution_mode']:10} {r['compliance']['compliance_score']:>4}  "
          f"{r['legal_review']['overall_risk_level']:9} {'sim' if f['pro_was_invoked'] else 'não':16} "
          f"{tempo:5.0f}s  US$ {f['estimated_cost_usd_routed']:.4f}")
print("-" * 86)

for nome, r, _ in linhas:
    if r["execution_mode"] != "LIVE_ADK":
        falhar(f"{nome} rodou em modo demonstração: {r.get('execution_detail', '')[:200]}")
velonet, technova = linhas[0][1], linhas[1][1]
if not technova["finops"]["pro_was_invoked"]:
    falhar("o TechNova deveria ter escalado para o Pro.")
if velonet["finops"]["pro_was_invoked"]:
    print("! o VeloNet também foi para o Pro nesta execução: o compliance achou algum alerta. Rode de novo.")
print("✓ o seu AuditOps está no ar, com agentes Gemini reais e a cascata Flash → Pro. Lab 07 concluído!")
