# 🛡️ AuditOps 2.0: Agentic RAG, Rastreamento de Página & Model Cascading no Google ADK

> **Veio para o workshop?** Comece pelo [workshop/README.md](workshop/README.md): 8 labs para construir os agentes passo a passo, publicar o AuditOps no seu próprio projeto GCP e explorar o banco vetorial no AlloyDB.

> **Projeto Google Bootcamp**: Orquestração Multi-Agente com **Google ADK**, **Busca em Banco Vetorial (RAG)** com citação exata de página do contrato, **Agente Assistente de Insights** e uma tela web para analisar contratos.

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

### 1. Abrir o frontend
```bash
python3 app_server.py
```
Depois, abra **`http://localhost:8080`** no navegador.

Na tela inicial, escolha um dos 8 contratos de exemplo ou envie o seu em PDF ou DOCX pelo botão **Enviar contrato**. A análise leva cerca de 1 minuto. Em seguida você vê a recomendação, os riscos com a página de cada um e as sugestões de negociação, e pode fazer perguntas sobre o contrato pelo botão **Perguntar sobre este contrato**.

Sem `GOOGLE_CLOUD_PROJECT` configurado, o app abre em modo demonstração, com análises de exemplo.

### 2. Executar o Showcase no Terminal (CLI)
```bash
python3 run_demo.py
```

### 3. Executar os Testes Automatizados
```bash
python3 -m unittest discover tests/ -v
```
