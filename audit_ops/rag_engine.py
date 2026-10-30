"""Motor de Busca Vetorial (Agentic RAG) com Google Cloud AlloyDB AI (pgvector + ScaNN) e Vertex AI.

Suporta:
1. Armazenamento e busca vetorial gerenciada no **AlloyDB for PostgreSQL** (`pgvector` 768 dims + `google_ml_integration`).
2. Indexação dos documentos da base corporativa (`knowledge_base/`) preservando número de página e seção.
3. Indexação dinâmica de contratos com extração exata da página (`page_number`) e cláusula (`section_id`).
4. Embeddings densos via Vertex AI (`text-embedding-004`, 768 dimensões) combinados com busca híbrida
   (Cosine Similarity `<=>` no AlloyDB + fallback híbrido em memória para zero downtime).
"""

import os
import re
import math
import hashlib
import logging
import threading
from collections import OrderedDict
from typing import List, Dict, Any, Optional
from collections import Counter


class VectorChunk:
    """Representa um fragmento indexado no banco vetorial com metadados de página."""

    def __init__(
        self,
        chunk_id: str,
        text: str,
        source_document: str,
        page_number: int = 1,
        section_id: str = "",
        category: str = "GENERAL",
        embedding: Optional[List[float]] = None
    ):
        self.chunk_id = chunk_id
        self.text = text.strip()
        self.source_document = source_document
        self.page_number = page_number
        self.section_id = section_id
        self.category = category
        self.embedding = embedding or []

    def to_dict(self, similarity_score: float = 0.0, storage_engine: str = "AlloyDB AI (pgvector)") -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source_document": self.source_document,
            "page_number": self.page_number,
            "section_id": self.section_id,
            "category": self.category,
            "similarity_score": round(similarity_score, 4),
            "citation_badge": f"Pág. {self.page_number}" + (f" • {self.section_id}" if self.section_id else ""),
            "storage_engine": storage_engine,
            "text": self.text,
        }


class LocalSemanticEmbedder:
    """Gerador de vetores semânticos determinísticos + sinônimos jurídicos para busca híbrida por cosseno."""

    SYNONYM_GROUPS = [
        {"lgpd", "dados", "pessoais", "privacidade", "vazamento", "incidente", "anpd", "dpa", "transferencia", "internacional", "48", "24"},
        {"sla", "disponibilidade", "uptime", "credito", "creditos", "service", "indisponibilidade", "99.5", "98.0", "99.8"},
        {"multa", "penalidade", "penalidades", "rescisao", "rescisoria", "antecipada", "fidelidade", "50%", "10%", "mora"},
        {"responsabilidade", "ilimitada", "indenizacao", "cap", "teto", "patrimonial", "lucros", "cessantes", "12", "meses"},
        {"foro", "jurisdicao", "arbitragem", "delaware", "nova", "york", "sao", "paulo", "legislacao", "aaa"},
        {"preco", "valor", "benchmark", "custo", "desconto", "sobrepreco", "180.000", "15.000", "anual", "mensal", "historico"},
    ]

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        clean = text.lower()
        replacements = {
            "á": "a", "à": "a", "ã": "a", "â": "a",
            "é": "e", "ê": "e", "í": "i",
            "ó": "o", "ô": "o", "õ": "o",
            "ú": "u", "ç": "c"
        }
        for k, v in replacements.items():
            clean = clean.replace(k, v)
        tokens = re.findall(r"[a-z0-9_%\.]+", clean)
        expanded = list(tokens)
        token_set = set(tokens)
        for idx, group in enumerate(cls.SYNONYM_GROUPS):
            overlap = len(token_set.intersection(group))
            if overlap > 0:
                expanded.extend([f"__sem_cluster_{idx}__"] * (overlap * 2))
        return expanded

    @classmethod
    def dense_cosine_similarity(cls, vec_a: List[float], vec_b: List[float]) -> float:
        """Calcula a similaridade de cosseno exata entre dois vetores densos (768 dimensões do text-embedding-004)."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if not norm_a or not norm_b:
            return 0.0
        return round(max(0.0, min(0.9999, dot / (norm_a * norm_b))), 4)

    @classmethod
    def cosine_similarity(cls, query: str, doc_text: str) -> float:
        q_tokens = cls.tokenize(query)
        d_tokens = cls.tokenize(doc_text)
        if not q_tokens or not d_tokens:
            return 0.0
        q_counts = Counter(q_tokens)
        d_counts = Counter(d_tokens)
        intersection = set(q_counts.keys()) & set(d_counts.keys())
        numerator = sum(q_counts[x] * d_counts[x] for x in intersection)
        sum1 = sum(v ** 2 for v in q_counts.values())
        sum2 = sum(v ** 2 for v in d_counts.values())
        denominator = math.sqrt(sum1) * math.sqrt(sum2)
        if not denominator:
            return 0.0
        raw_sim = numerator / denominator
        return round(min(0.99, raw_sim), 4)


# Carteira de exemplo usada para popular o AlloyDB: fonte única para a aplicação e para
# o pacote de carga da equipe de infra (`sql/gerar_pacote_alloydb.py`)
SEED_SUPPLIERS: List[Dict[str, str]] = [
    {"supplier_id": "SUP-001", "company_name": "TechNova Cloud Solutions Inc.", "cnpj": "12.345.678/0001-90", "service_category": "SaaS Logístico Enterprise", "risk_tier": "CRITICAL"},
    {"supplier_id": "SUP-002", "company_name": "PaySphere Instituição de Pagamento S.A.", "cnpj": "23.456.789/0001-01", "service_category": "Gateway Pagamentos & Pix", "risk_tier": "HIGH"},
    {"supplier_id": "SUP-003", "company_name": "Aegis CyberDefense Ltda.", "cnpj": "34.567.890/0001-12", "service_category": "Cibersegurança SOC 24x7", "risk_tier": "MODERATE"},
    {"supplier_id": "SUP-004", "company_name": "CloudCore Infraestrutura S.A.", "cnpj": "45.678.901/0001-23", "service_category": "Suporte TI Cloud", "risk_tier": "LOW"},
    {"supplier_id": "SUP-005", "company_name": "PeopleFirst Cloud HCM Brasil Ltda.", "cnpj": "56.789.012/0001-34", "service_category": "Gestão de RH & Folha", "risk_tier": "LOW"},
    {"supplier_id": "SUP-006", "company_name": "NeuralForge AI Compute Corp.", "cnpj": "67.890.123/0001-45", "service_category": "Cluster GPU H100 & APIs LLM", "risk_tier": "CRITICAL"},
    {"supplier_id": "SUP-007", "company_name": "TitanERP Sistemas Corporativos S.A.", "cnpj": "78.901.234/0001-56", "service_category": "ERP Financeiro & SPED Fiscal", "risk_tier": "HIGH"},
    {"supplier_id": "SUP-008", "company_name": "VeloNet Telecomunicações Empresariais S.A.", "cnpj": "89.012.345/0001-67", "service_category": "Conectividade SD-WAN & Links 5G", "risk_tier": "LOW"},
]

SEED_CONTRACTS: List[Dict[str, Any]] = [
    {"contract_id": "CTR-2026-001", "supplier_id": "SUP-001", "file": "contrato_saas_enterprise", "title": "Contrato SaaS Logístico Enterprise — TechNova", "annual_value_brl": 180000.00, "total_pages": 5},
    {"contract_id": "CTR-2026-002", "supplier_id": "SUP-002", "file": "contrato_fintech_openfinance", "title": "Contrato Gateway Pagamentos & Pix — PaySphere", "annual_value_brl": 360000.00, "total_pages": 4},
    {"contract_id": "CTR-2026-003", "supplier_id": "SUP-003", "file": "contrato_cybersec_soc", "title": "Contrato Cibersegurança SOC 24x7 — Aegis", "annual_value_brl": 264000.00, "total_pages": 4},
    {"contract_id": "CTR-2026-004", "supplier_id": "SUP-004", "file": "contrato_padrao_sla", "title": "Contrato Suporte TI Cloud — CloudCore", "annual_value_brl": 102000.00, "total_pages": 3},
    {"contract_id": "CTR-2026-005", "supplier_id": "SUP-005", "file": "contrato_rh_cloud", "title": "Contrato Gestão de RH & Folha — PeopleFirst", "annual_value_brl": 144000.00, "total_pages": 4},
    {"contract_id": "CTR-2026-006", "supplier_id": "SUP-006", "file": "contrato_ia_generativa_gpu", "title": "Contrato Cluster GPU H100 & APIs LLM — NeuralForge AI", "annual_value_brl": 620000.00, "total_pages": 5},
    {"contract_id": "CTR-2026-007", "supplier_id": "SUP-007", "file": "contrato_erp_fiscal_cloud", "title": "Contrato ERP Financeiro & Motor Tributário SPED — TitanERP", "annual_value_brl": 480000.00, "total_pages": 4},
    {"contract_id": "CTR-2026-008", "supplier_id": "SUP-008", "file": "contrato_telecom_sdwan", "title": "Contrato Conectividade Dedicada SD-WAN & 5G — VeloNet", "annual_value_brl": 216000.00, "total_pages": 3},
]


def contract_gcs_uri(file_stem: str, bucket: Optional[str] = None) -> str:
    """URI do PDF do contrato no bucket de ingestão (padrão: `<projeto>-contracts`)."""
    if not bucket:
        bucket = os.getenv("CONTRACTS_BUCKET") or f"{os.getenv('GOOGLE_CLOUD_PROJECT', 'auditops')}-contracts"
    return f"gs://{bucket.removeprefix('gs://').rstrip('/')}/pdf/{file_stem}.pdf"


MAX_CACHED_CONTRACTS = 64


def contract_key(contract_text: str) -> str:
    """Chave estável do contrato (hash do texto): separa trechos e relatórios de contratos diferentes."""
    return "doc-" + hashlib.sha1(contract_text.strip().encode("utf-8")).hexdigest()[:16]


class AlloyDBVectorAdapter:
    """Conector gerenciado para Google Cloud AlloyDB for PostgreSQL (`pgvector` + `google_ml_integration`)."""

    def __init__(self):
        self.host = os.getenv("ALLOYDB_HOST", "").strip()
        self.port = int(os.getenv("ALLOYDB_PORT", "5432"))
        self.dbname = os.getenv("ALLOYDB_DB", "postgres")
        self.user = os.getenv("ALLOYDB_USER", "postgres")
        self.password = os.getenv("ALLOYDB_PASSWORD", "")
        self.cluster_name = os.getenv("ALLOYDB_CLUSTER", "auditops-alloydb-cluster")
        self.instance_name = os.getenv("ALLOYDB_INSTANCE", "auditops-alloydb-primary")
        self._conn = None
        self.is_connected = False
        self.last_status_message = "AlloyDB AI configurado em modo Hybrid Standby (defina ALLOYDB_HOST para conexão VPC direta)"
        if self.host:
            self._try_connect_and_init()

    def _try_connect_and_init(self) -> bool:
        try:
            import psycopg2
            self._conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                connect_timeout=3
            )
            self._conn.autocommit = True
            with self._conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS suppliers (
                        supplier_id VARCHAR(64) PRIMARY KEY,
                        company_name VARCHAR(160) NOT NULL,
                        cnpj VARCHAR(32),
                        service_category VARCHAR(64) NOT NULL,
                        risk_tier VARCHAR(32) DEFAULT 'PENDING',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS contracts_metadata (
                        contract_id VARCHAR(64) PRIMARY KEY,
                        supplier_id VARCHAR(64) REFERENCES suppliers(supplier_id),
                        title VARCHAR(200) NOT NULL,
                        gcs_uri VARCHAR(300) NOT NULL,
                        annual_value_brl NUMERIC(14, 2) DEFAULT 0,
                        total_pages INT DEFAULT 1,
                        processing_status VARCHAR(32) NOT NULL DEFAULT 'VECTORIZED',
                        extracted_text TEXT,
                        ingested_at TIMESTAMPTZ DEFAULT NOW(),
                        audited_at TIMESTAMPTZ
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS auditops_vector_chunks (
                        chunk_id VARCHAR(128) PRIMARY KEY,
                        contract_id VARCHAR(64),
                        source_type VARCHAR(32) NOT NULL,
                        source_document VARCHAR(160) NOT NULL,
                        page_number INT NOT NULL DEFAULT 1,
                        section_id VARCHAR(160) DEFAULT '',
                        category VARCHAR(64) DEFAULT 'GERAL',
                        text_content TEXT NOT NULL,
                        embedding vector(768),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS auditops_finops_telemetry (
                        audit_id SERIAL PRIMARY KEY,
                        contract_id VARCHAR(64),
                        contract_name VARCHAR(200) NOT NULL,
                        compliance_score INT NOT NULL,
                        overall_risk_level VARCHAR(32) NOT NULL,
                        escalated_to_pro BOOLEAN NOT NULL,
                        model_tier_flash VARCHAR(64) NOT NULL,
                        model_tier_pro VARCHAR(64) NOT NULL,
                        routed_cost_usd NUMERIC(10, 6) NOT NULL,
                        baseline_pro_cost_usd NUMERIC(10, 6) NOT NULL,
                        savings_percentage NUMERIC(5, 2) NOT NULL,
                        total_latency_ms INT NOT NULL,
                        audited_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                # Bancos criados por versões antigas da aplicação não tinham `contract_id`, e sem ela
                # a carga do pacote de infra (`sql/`) falha
                cur.execute("ALTER TABLE auditops_vector_chunks ADD COLUMN IF NOT EXISTS contract_id VARCHAR(64);")
                cur.execute("ALTER TABLE auditops_finops_telemetry ADD COLUMN IF NOT EXISTS contract_id VARCHAR(64);")
                cur.executemany(
                    """
                    INSERT INTO suppliers (supplier_id, company_name, cnpj, service_category, risk_tier)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (supplier_id) DO NOTHING;
                    """,
                    [(s["supplier_id"], s["company_name"], s["cnpj"], s["service_category"], s["risk_tier"])
                     for s in SEED_SUPPLIERS],
                )
                # DO UPDATE corrige valores de cargas antigas (ex.: Aegis e CloudCore estavam errados)
                cur.executemany(
                    """
                    INSERT INTO contracts_metadata
                        (contract_id, supplier_id, title, gcs_uri, annual_value_brl, total_pages, processing_status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'VECTORIZED')
                    ON CONFLICT (contract_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        annual_value_brl = EXCLUDED.annual_value_brl,
                        total_pages = EXCLUDED.total_pages;
                    """,
                    [(c["contract_id"], c["supplier_id"], c["title"], contract_gcs_uri(c["file"]),
                      c["annual_value_brl"], c["total_pages"]) for c in SEED_CONTRACTS],
                )
            self.is_connected = True
            self.last_status_message = f"Conectado ao AlloyDB AI ({self.host}:{self.port}/{self.dbname}) • pgvector 768-d ativo"
            return True
        except Exception as exc:
            self.is_connected = False
            self.last_status_message = f"Fallback Híbrido Ativo (AlloyDB VPC {self.host} indisponível no momento: {type(exc).__name__})"
            return False

    @staticmethod
    def _format_pgvector(vec: List[float]) -> Optional[str]:
        if not vec or len(vec) != 768:
            return None
        return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"

    def upsert_chunks(
        self,
        chunks: List[VectorChunk],
        source_type: str = "KNOWLEDGE_BASE",
        contract_id: Optional[str] = None,
    ) -> int:
        """Grava trechos no AlloyDB. Com `contract_id`, só substitui os trechos daquele contrato
        (auditorias simultâneas de contratos diferentes não apagam os trechos umas das outras)."""
        if not self.is_connected or not self._conn:
            return 0
        count = 0
        try:
            with self._conn.cursor() as cur:
                if source_type == "CONTRACT" and contract_id:
                    cur.execute(
                        "DELETE FROM auditops_vector_chunks WHERE source_type = 'CONTRACT' AND contract_id = %s;",
                        (contract_id,),
                    )
                    # Contratos auditados ficam guardados por 7 dias; a carga de exemplo (CTR-*) não expira
                    cur.execute(
                        "DELETE FROM auditops_vector_chunks WHERE source_type = 'CONTRACT' "
                        "AND contract_id LIKE 'doc-%%' AND updated_at < NOW() - INTERVAL '7 days';"
                    )
                elif source_type == "CONTRACT":
                    cur.execute("DELETE FROM auditops_vector_chunks WHERE source_type = 'CONTRACT';")
                for c in chunks:
                    vec_str = self._format_pgvector(c.embedding)
                    # O mesmo nome de arquivo pode aparecer em contratos diferentes: prefixa o id com a chave
                    row_id = f"{contract_id}/{c.chunk_id}" if contract_id else c.chunk_id
                    cur.execute(
                        """
                        INSERT INTO auditops_vector_chunks
                            (chunk_id, contract_id, source_type, source_document, page_number, section_id, category, text_content, embedding, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector, NOW())
                        ON CONFLICT (chunk_id) DO UPDATE SET
                            page_number = EXCLUDED.page_number,
                            section_id = EXCLUDED.section_id,
                            category = EXCLUDED.category,
                            text_content = EXCLUDED.text_content,
                            embedding = COALESCE(EXCLUDED.embedding, auditops_vector_chunks.embedding),
                            updated_at = NOW();
                        """,
                        (row_id, contract_id, source_type, c.source_document, c.page_number, c.section_id, c.category, c.text, vec_str)
                    )
                    count += 1
        except Exception:
            pass
        return count

    def query_similar_chunks(
        self,
        query_vec: List[float],
        source_type: str = "KNOWLEDGE_BASE",
        category: Optional[str] = None,
        top_k: int = 4,
        contract_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self.is_connected or not self._conn or not query_vec or len(query_vec) != 768:
            return []
        vec_str = self._format_pgvector(query_vec)
        try:
            with self._conn.cursor() as cur:
                if contract_id:
                    cur.execute(
                        """
                        SELECT chunk_id, source_document, page_number, section_id, category, text_content,
                               1 - (embedding <=> %s::vector) AS sim_score
                        FROM auditops_vector_chunks
                        WHERE source_type = %s AND contract_id = %s AND embedding IS NOT NULL
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s;
                        """,
                        (vec_str, source_type, contract_id, vec_str, top_k)
                    )
                elif category and category.upper() not in ("ALL", "GERAL"):
                    cur.execute(
                        """
                        SELECT chunk_id, source_document, page_number, section_id, category, text_content,
                               1 - (embedding <=> %s::vector) AS sim_score
                        FROM auditops_vector_chunks
                        WHERE source_type = %s AND embedding IS NOT NULL AND category = %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s;
                        """,
                        (vec_str, source_type, category.upper(), vec_str, top_k)
                    )
                else:
                    cur.execute(
                        """
                        SELECT chunk_id, source_document, page_number, section_id, category, text_content,
                               1 - (embedding <=> %s::vector) AS sim_score
                        FROM auditops_vector_chunks
                        WHERE source_type = %s AND embedding IS NOT NULL
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s;
                        """,
                        (vec_str, source_type, vec_str, top_k)
                    )
                rows = cur.fetchall()
                results = []
                for row in rows:
                    c_id, src_doc, page_num, sec_id, cat, txt, sim = row
                    if contract_id:
                        c_id = c_id.split("/", 1)[-1]
                    sim_val = round(max(0.0, min(0.9999, float(sim or 0.0))), 4)
                    results.append({
                        "chunk_id": c_id,
                        "source_document": src_doc,
                        "page_number": int(page_num),
                        "section_id": sec_id,
                        "category": cat,
                        "similarity_score": sim_val,
                        "citation_badge": f"Pág. {page_num}" + (f" • {sec_id}" if sec_id else ""),
                        "storage_engine": "AlloyDB PostgreSQL (pgvector <=> cosine)",
                        "text": txt,
                    })
                return results
        except Exception:
            return []

    def record_finops_audit(self, report_dict: Dict[str, Any]) -> bool:
        if not self.is_connected or not self._conn:
            return False
        try:
            fin = report_dict.get("finops") or report_dict.get("finops_metrics") or {}
            comp = report_dict.get("compliance") or {}
            leg = report_dict.get("legal_review") or {}
            total_lat_sec = (
                float(fin.get("tier1_latency_sec", 0.0))
                + float(fin.get("tier2_latency_sec", 0.0))
                + float(fin.get("tier3_latency_sec", 0.0))
            ) or float(fin.get("total_latency_sec", 0.0))
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auditops_finops_telemetry
                        (contract_name, compliance_score, overall_risk_level, escalated_to_pro,
                         model_tier_flash, model_tier_pro, routed_cost_usd, baseline_pro_cost_usd,
                         savings_percentage, total_latency_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        report_dict.get("contract_name") or report_dict.get("contract_title", "Contrato Corporativo"),
                        int(comp.get("compliance_score", report_dict.get("compliance_score", 0))),
                        str(leg.get("overall_risk_level", report_dict.get("overall_risk_level", "MODERATE"))),
                        bool(fin.get("pro_was_invoked", fin.get("escalated_to_pro", False))),
                        str(fin.get("tier1_model", fin.get("tier_1_model", "gemini-3.8-flash"))),
                        str(fin.get("tier3_model", fin.get("tier_2_model", "gemini-3.1-pro-preview"))),
                        float(fin.get("estimated_cost_usd_routed", fin.get("estimated_cost_routed_usd", 0.0))),
                        float(fin.get("estimated_cost_usd_all_pro", fin.get("estimated_cost_all_pro_usd", 0.0))),
                        float(fin.get("estimated_cost_savings_pct", fin.get("cost_savings_pct", 0.0))),
                        int(total_lat_sec * 1000),
                    )
                )
            return True
        except Exception:
            return False


class AuditOpsVectorEngine:
    """Motor Vetorial Híbrido: Google Cloud AlloyDB AI (pgvector) + Vertex AI Embeddings (768-d) + Rastreamento de Página."""

    def __init__(self, knowledge_dir: Optional[str] = None):
        if knowledge_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            knowledge_dir = os.path.join(base_dir, "knowledge_base")
        self.knowledge_dir = knowledge_dir
        self.kb_chunks: List[VectorChunk] = []
        self.contract_chunks: List[VectorChunk] = []   # último contrato indexado (tela de busca e ferramentas ADK)
        self._contracts: "OrderedDict[str, List[VectorChunk]]" = OrderedDict()
        self._contracts_lock = threading.Lock()
        self._embedding_cache: Dict[str, List[float]] = {}
        self._embedding_error_logged = False
        self._genai_client = None
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
        self.alloydb = AlloyDBVectorAdapter()
        self._load_and_index_knowledge_base()

    def get_engine_metadata(self) -> Dict[str, Any]:
        """Retorna os metadados arquiteturais do banco vetorial para exibição na aba técnica e APIs."""
        return {
            "vector_database": "Google Cloud AlloyDB for PostgreSQL (AlloyDB AI)",
            "extensions": ["vector (pgvector 0.7+)", "alloydb_scann", "google_ml_integration"],
            "index_type": "ScaNN / HNSW (vector_cosine_ops <=>)",
            "embedding_model": self.embedding_model,
            "embedding_dimensions": 768,
            "alloydb_cluster": self.alloydb.cluster_name,
            "alloydb_instance": self.alloydb.instance_name,
            "alloydb_host": self.alloydb.host or "VPC Direct Egress / Hybrid Standby",
            "live_pg_connection": self.alloydb.is_connected,
            "status_summary": self.alloydb.last_status_message,
            "indexed_kb_chunks": len(self.kb_chunks),
            "indexed_contract_chunks": len(self.contract_chunks),
            "sample_sql_query": (
                "SELECT chunk_id, page_number, section_id, "
                "1 - (embedding <=> embedding('text-embedding-004', $1)::vector) AS cosine_similarity "
                "FROM auditops_vector_chunks WHERE source_type = 'CONTRACT' "
                "ORDER BY embedding <=> embedding('text-embedding-004', $1)::vector LIMIT 4;"
            )
        }

    # Trechos por chamada em lote: o text-embedding-004 aceita até 20 mil tokens por requisição
    EMBED_BATCH_SIZE = 20

    def _get_cloud_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Gera vetores densos (768 dims) no Vertex AI em lote: uma chamada para vários textos.

        Uma chamada por trecho custava ~1s cada e, numa auditoria, somava dezenas de chamadas em sequência.
        """
        if not texts or not (os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GEMINI_API_KEY")):
            return [None] * len(texts)
        results: List[Optional[List[float]]] = [self._embedding_cache.get(t[:300]) for t in texts]
        pending = [i for i, vec in enumerate(results) if vec is None]
        try:
            # Cliente reutilizado: criar um genai.Client por chamada custa ~11s (descoberta de credenciais ADC)
            if self._genai_client is None:
                from google import genai
                self._genai_client = genai.Client()
            for start in range(0, len(pending), self.EMBED_BATCH_SIZE):
                batch = pending[start:start + self.EMBED_BATCH_SIZE]
                resp = self._genai_client.models.embed_content(
                    model=self.embedding_model,
                    contents=[texts[i][:2000] for i in batch]
                )
                for i, emb in zip(batch, resp.embeddings or []):
                    vec = list(emb.values)
                    self._embedding_cache[texts[i][:300]] = vec
                    results[i] = vec
        except Exception as e:
            if not self._embedding_error_logged:
                logging.getLogger("audit_ops").warning(
                    "Embeddings Vertex indisponíveis, usando busca híbrida local: %s: %s", type(e).__name__, e
                )
                self._embedding_error_logged = True
        return results

    def _get_cloud_embedding(self, text: str) -> Optional[List[float]]:
        """Gera o vetor denso de um único texto (ex.: a pergunta da busca)."""
        return self._get_cloud_embeddings([text])[0]

    def warm_up(self) -> None:
        """Cria o cliente do Gemini e gera os vetores da base antes da primeira auditoria (roda em segundo plano)."""
        if os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GEMINI_API_KEY"):
            self._embed_missing(self.kb_chunks)

    def _embed_missing(self, chunks: List[VectorChunk]) -> None:
        """Preenche em lote o embedding dos trechos que ainda não têm vetor."""
        missing = [c for c in chunks if not c.embedding]
        vectors = self._get_cloud_embeddings([f"{c.section_id}\n{c.text}" for c in missing])
        for c, vec in zip(missing, vectors):
            c.embedding = vec or []

    def _parse_paginated_markdown(self, content: str, source_name: str, is_contract: bool = False) -> List[VectorChunk]:
        """Divide um documento Markdown por páginas (`--- [Página X] ---`) e seções/cláusulas."""
        chunks: List[VectorChunk] = []
        current_page = 1
        lines = content.splitlines()

        current_section_title = "Preâmbulo / Identificação"
        current_buffer: List[str] = []
        chunk_counter = 1

        page_pattern = re.compile(r"---\s*\[P.+?gina\s*(\d+)\]\s*---", re.IGNORECASE)
        header_pattern = re.compile(r"^(#{2,3})\s+(.+)$")

        def flush_buffer(page_num: int, sec_title: str, buf: List[str]):
            nonlocal chunk_counter
            text_block = "\n".join(buf).strip()
            if not text_block or len(text_block) < 15:
                return
            category = self._infer_category(sec_title + " " + text_block)
            c_id = f"{source_name}#p{page_num}_c{chunk_counter}"
            chunk_counter += 1
            chunks.append(
                VectorChunk(
                    chunk_id=c_id,
                    text=text_block,
                    source_document=source_name,
                    page_number=page_num,
                    section_id=sec_title,
                    category=category
                )
            )

        for line in lines:
            page_match = page_pattern.search(line)
            if page_match:
                flush_buffer(current_page, current_section_title, current_buffer)
                current_buffer = []
                current_page = int(page_match.group(1))
                continue

            header_match = header_pattern.match(line.strip())
            if header_match:
                flush_buffer(current_page, current_section_title, current_buffer)
                current_buffer = [line]
                current_section_title = header_match.group(2).strip()
                continue

            current_buffer.append(line)

        flush_buffer(current_page, current_section_title, current_buffer)
        return chunks

    @staticmethod
    def _infer_category(text: str) -> str:
        t = text.upper()
        if any(k in t for k in ["LGPD", "DADOS PESSOAIS", "PRIVACIDADE", "DPA"]):
            return "LGPD"
        if any(k in t for k in ["SLA", "DISPONIBILIDADE", "UPTIME", "NÍVEL DE SERVIÇO", "NÍVEIS DE SERVIÇO"]):
            return "SLA"
        if any(k in t for k in ["RESPONSABILIDADE", "INDENIZAÇÃO", "LIABILITY", "CAP"]):
            return "RESPONSABILIDADE"
        if any(k in t for k in ["FORO", "JURISDIÇÃO", "DELAWARE", "ARBITRAGEM"]):
            return "FORO"
        if any(k in t for k in ["PENALIDADE", "MULTA", "RESCISÃO"]):
            return "PENALIDADES"
        if any(k in t for k in ["BENCHMARK", "VALOR", "PREÇO", "PAGAMENTO"]):
            return "FINANCEIRO"
        return "GERAL"

    def _load_and_index_knowledge_base(self) -> None:
        """Indexa todos os documentos da pasta `knowledge_base/` e sincroniza com o AlloyDB se conectado."""
        self.kb_chunks = []
        if not os.path.isdir(self.knowledge_dir):
            return
        for fname in sorted(os.listdir(self.knowledge_dir)):
            if fname.endswith(".md"):
                fpath = os.path.join(self.knowledge_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                doc_chunks = self._parse_paginated_markdown(content, source_name=fname, is_contract=False)
                self.kb_chunks.extend(doc_chunks)
        if self.alloydb.is_connected:
            self._embed_missing(self.kb_chunks)
            self.alloydb.upsert_chunks(self.kb_chunks, source_type="KNOWLEDGE_BASE")

    def index_contract(self, contract_text: str, contract_name: str = "Contrato_Analisado.md") -> List[Dict[str, Any]]:
        """Indexa as páginas e cláusulas do contrato em análise e persiste no AlloyDB quando ativo."""
        chunks = self._parse_paginated_markdown(
            contract_text,
            source_name=contract_name,
            is_contract=True
        )
        key = contract_key(contract_text)
        with self._contracts_lock:
            self._contracts[key] = chunks
            self._contracts.move_to_end(key)
            while len(self._contracts) > MAX_CACHED_CONTRACTS:
                self._contracts.popitem(last=False)
        self.contract_chunks = chunks
        if self.alloydb.is_connected:
            self._embed_missing(chunks)
            self.alloydb.upsert_chunks(chunks, source_type="CONTRACT", contract_id=key)
        return [c.to_dict(similarity_score=1.0) for c in chunks]

    def search_knowledge_base(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """Busca semântica híbrida: AlloyDB pgvector (`<=>`) + Vertex AI Embeddings (768-d) + Grounding Léxico."""
        query_dense_vec = self._get_cloud_embedding(query)

        # 1. Se o AlloyDB estiver conectado com embeddings densos, consulta diretamente via pgvector (<=>)
        if self.alloydb.is_connected and query_dense_vec:
            pg_hits = self.alloydb.query_similar_chunks(
                query_vec=query_dense_vec,
                source_type="KNOWLEDGE_BASE",
                category=category,
                top_k=top_k
            )
            if pg_hits:
                return pg_hits

        # 2. Execução Híbrida (Vertex AI 768-d + Similaridade de Cosseno Semântica)
        if query_dense_vec:
            self._embed_missing(self.kb_chunks)
        scored = []
        for chunk in self.kb_chunks:
            lexical_sim = LocalSemanticEmbedder.cosine_similarity(query, f"{chunk.section_id} {chunk.text}")
            if query_dense_vec:
                dense_sim = LocalSemanticEmbedder.dense_cosine_similarity(query_dense_vec, chunk.embedding)
                sim = (dense_sim * 0.65) + (lexical_sim * 0.35) if dense_sim > 0 else lexical_sim
            else:
                sim = lexical_sim

            if category and category.upper() not in ("ALL", "GERAL") and chunk.category != category.upper():
                sim = sim * 0.85
            elif category and category.upper() == chunk.category:
                sim = min(0.99, sim + 0.08)
            scored.append((sim, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk.to_dict(similarity_score=sim) for sim, chunk in scored[:top_k] if sim > 0.0]

    def search_contract_pages(self, query: str, top_k: int = 3, contract_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Localiza em qual página e cláusula do contrato está uma determinada informação (AlloyDB pgvector + Hybrid RAG).

        Com `contract_id` (de `contract_key`), busca só nos trechos daquele contrato; sem ele, no último indexado.
        """
        if contract_id:
            with self._contracts_lock:
                chunks = self._contracts.get(contract_id, [])
        else:
            chunks = self.contract_chunks
        query_dense_vec = self._get_cloud_embedding(query)

        if self.alloydb.is_connected and query_dense_vec:
            pg_hits = self.alloydb.query_similar_chunks(
                query_vec=query_dense_vec,
                source_type="CONTRACT",
                category=None,
                top_k=top_k,
                contract_id=contract_id,
            )
            if pg_hits:
                return pg_hits

        if query_dense_vec:
            self._embed_missing(chunks)
        scored = []
        for chunk in chunks:
            lexical_sim = LocalSemanticEmbedder.cosine_similarity(query, f"{chunk.section_id} {chunk.text}")
            if query_dense_vec:
                dense_sim = LocalSemanticEmbedder.dense_cosine_similarity(query_dense_vec, chunk.embedding)
                sim = (dense_sim * 0.65) + (lexical_sim * 0.35) if dense_sim > 0 else lexical_sim
            else:
                sim = lexical_sim
            scored.append((sim, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk.to_dict(similarity_score=sim) for sim, chunk in scored[:top_k] if sim > 0.0]


# Instância singleton global do motor vetorial
GLOBAL_VECTOR_ENGINE = AuditOpsVectorEngine()
