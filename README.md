# 🛡️ AuditOps 2.0: Agentic RAG, Rastreamento de Página & Model Cascading no Google ADK

> **Projeto Google Bootcamp**: Orquestração Multi-Agente com **Google ADK**, **Busca em Banco Vetorial (RAG)** com citação exata de página do contrato, **Agente Assistente de Insights** e **Frontend Moderno**.

---

## 🎯 Arquitetura & Regra de Negócio (`Flash 3.8` $\rightarrow$ `3.1 Pro`)

1. **Camada Flash (`gemini-3.8-flash`):**
   - **`extractor_agent`**: Lê o contrato paginado e mapeia de qual **página exata (`contract_page`)** saiu cada cláusula, valor e foro.
   - **`compliance_rag_agent`**: Faz busca semântica no **Banco Vetorial (`knowledge_base/`)** para validar as 5 regras de ouro corporativas (LGPD, SLA $\ge 99,5\%$, Multa $\le 10\%$, Liability Cap de 12 meses e Foro em SP).
2. **Gatilho de Escalonamento (Regra de Negócio):**
   - **Rota Fast-Track (`Score >= 80` e sem cláusula leonina):** O contrato é aprovado na camada Flash em ~1s sem acionar o modelo Pro (**>85% de economia FinOps**).
   - **Rota Crítica (`Score < 80` ou Responsabilidade Ilimitada / Foro Delaware / Violação LGPD):** Escala automaticamente para o **`gemini-3.1-pro-preview`** enviando apenas os desvios e os *chunks* do banco vetorial.
3. **Camada de Raciocínio Profundo & Assistente de Insights (`gemini-3.1-pro-preview`):**
   - **`legal_risk_pro_agent`**: Redige as *redlines* substitutivas citando a página do contrato e o documento do Banco Vetorial.
   - **`insight_assistant_agent`**: Cruza o contrato com o histórico vetorial de compras (*Procurement*), detecta sobrepreço, sugere alavancas de negociação (*trade-offs*) e responde perguntas via Chat citando a página exata do contrato.

---

## 🚀 Como Executar

> **Workshop:** para construir os agentes passo a passo e publicar o AuditOps no seu próprio projeto GCP, siga o [workshop](workshop/README.md).

### 1. Abrir o Frontend Moderno e Elegante (Web UI + Chat Insights)
```bash
python3 app_server.py
```
Acesse no navegador: **`http://localhost:8080`**

No Frontend você pode:
- Alternar entre o **Contrato SaaS Enterprise (Crítico $\rightarrow$ Escala p/ 3.1 Pro)** e o **Contrato Padrão TI (Conforme $\rightarrow$ Resolve no Flash 3.8)**;
- Clicar nas badges **`📄 Pág. X`** em qualquer achado, redline ou insight para destacar a página correspondente no contrato;
- Inspecionar os *chunks* do **Banco Vetorial (RAG)** em tempo real;
- Conversar com o **Agente Assistente de Insights** no painel lateral.

### 2. Executar o Showcase no Terminal (CLI)
```bash
python3 run_demo.py
```

### 3. Executar os Testes Automatizados
```bash
python3 -m unittest discover tests/ -v
```
