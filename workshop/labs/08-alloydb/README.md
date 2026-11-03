# Lab 08: o banco vetorial por dentro (AlloyDB)

**Tempo:** 15 minutos

**A ideia:** no Lab 03, a busca nas páginas do contrato rodava numa lista em memória. No AuditOps de verdade, os trechos dos contratos e das políticas ficam no **AlloyDB**, o banco PostgreSQL do Google Cloud, cada um com o seu **vetor**: uma lista de 768 números que representa o significado do texto. Neste lab, você abre o banco e vê tudo isso com SQL, numa tela do próprio console.

```
  contrato ─► trechos ─► vetores (text-embedding) ─► AlloyDB ◄── busca por significado (SQL <=>)
```

> **Antes de começar:** o AlloyDB precisa estar pronto, e o app do Lab 07 precisa estar no ar. Ele foi criado lá na capa do workshop, com `lab alloydb`.

## Passo 1: conferir o banco e o app

```bash
lab alloydb
```

Deve aparecer `✓ AlloyDB pronto`. Se ainda estiver sendo criado, espere: o `lab alloydb` mostra o andamento.

Depois, entre no lab e confira se o app está usando o banco:

```bash
lab 08
python verificar.py
```

```
✓ o app está conectado ao AlloyDB (auditops-alloydb-primary)
  22 trechos de políticas indexados, vetores de 768 dimensões (text-embedding-004)
… auditando o contrato da VeloNet (cerca de 30 segundos)
✓ auditoria gravada no banco em 27s (nota 100, risco BAIXO)
```

O script também faz uma auditoria, para o banco ter dados frescos para você explorar.

> Apareceu `o app não está conectado ao AlloyDB`? Em geral, o app foi publicado antes de o banco ficar pronto. Publique de novo: `lab 07` e depois `./deploy_gcp.sh`. O deploy encontra o banco e conecta sozinho.

## Passo 2: abrir o AlloyDB Studio

O AlloyDB Studio é um editor de SQL dentro do console do Google Cloud.

1. Pegue a senha do banco no terminal: `lab alloydb senha`
2. No console (https://console.cloud.google.com), abra o menu e vá em **AlloyDB**.
3. Clique no cluster **auditops-alloydb-cluster** e, no menu da esquerda, em **AlloyDB Studio**.
4. Entre com:
   - **Banco de dados:** `postgres`
   - **Usuário:** `postgres`
   - **Senha:** a do passo 1

Abre um editor. Cole cada consulta abaixo, clique em **Executar** e leia o resultado.

## Passo 3: explorar com SQL

**3.1 O que tem no banco?**

```sql
SELECT source_type, COUNT(*) AS trechos
FROM auditops_vector_chunks
GROUP BY source_type;
```

`KNOWLEDGE_BASE` são os trechos das políticas da empresa. `CONTRACT` são os trechos dos contratos que você auditou.

**3.2 Como é um vetor?**

```sql
SELECT source_document, page_number,
       LEFT(text_content, 60)    AS trecho,
       vector_dims(embedding)    AS dimensoes,
       LEFT(embedding::text, 50) AS comeco_do_vetor
FROM auditops_vector_chunks
WHERE source_type = 'CONTRACT'
LIMIT 5;
```

Cada trecho virou 768 números. Textos com significado parecido têm números parecidos, mesmo com palavras diferentes.

**3.3 Busca por significado**

Esta consulta pega o trecho de uma política sobre **multa** e procura no banco os trechos de significado mais próximo. O operador `<=>` mede a distância entre dois vetores: quanto menor, mais parecidos.

```sql
WITH alvo AS (
  SELECT embedding FROM auditops_vector_chunks
  WHERE source_type = 'KNOWLEDGE_BASE' AND text_content ILIKE '%multa%'
  LIMIT 1
)
SELECT c.source_type, c.source_document, c.page_number,
       ROUND((1 - (c.embedding <=> alvo.embedding))::numeric, 3) AS similaridade,
       LEFT(c.text_content, 80) AS trecho
FROM auditops_vector_chunks c, alvo
WHERE c.embedding IS NOT NULL
ORDER BY c.embedding <=> alvo.embedding
LIMIT 5;
```

O primeiro resultado é o próprio trecho de partida (similaridade 1). Os seguintes são os de significado mais próximo: em geral, trechos de contratos e políticas sobre rescisão e penalidades, mesmo quando não usam a palavra "multa". É a mesma ideia do Lab 03, agora por significado em vez de palavras em comum.

Troque `'%multa%'` por `'%dados%'` ou `'%foro%'` e rode de novo.

**3.4 O histórico de custos**

Cada auditoria que o app faz fica registrada, com o modelo usado e o custo estimado:

```sql
SELECT contract_name, compliance_score, overall_risk_level,
       escalated_to_pro, routed_cost_usd, audited_at
FROM auditops_finops_telemetry
ORDER BY audited_at DESC
LIMIT 10;
```

`escalated_to_pro` mostra a cascata do Lab 05 na prática: contratos com risco foram para o Pro, e os limpos ficaram no Flash.

## Passo 4 (opcional): crie um índice vetorial

Com poucos trechos, o banco compara a busca com todos eles, um por um, e mesmo assim é rápido. Com milhões de trechos, isso fica lento. Para esse caso existe o **índice HNSW**, que encontra os vizinhos mais próximos sem olhar todos:

```sql
CREATE INDEX IF NOT EXISTS idx_trechos_hnsw
ON auditops_vector_chunks
USING hnsw (embedding vector_cosine_ops);

SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'auditops_vector_chunks';
```

Rode de novo a busca do passo 3.3: o resultado é o mesmo. A diferença só aparece em volumes grandes.

## Passo 5: apagar tudo (obrigatório)

O AlloyDB cobra por hora enquanto existir. No fim do workshop, rode:

```bash
lab limpar
```

O comando lista o que vai apagar e pede que você digite o ID do projeto para confirmar:

- o app no Cloud Run e a imagem dele;
- o AlloyDB e a senha, **só se foi você quem criou** o banco com `lab alloydb`. Se a infra criou, ele fica, e a infra cuida dele.

## Travou?

| O que aparece | O que fazer |
|---|---|
| `✗ não achei o serviço auditops-executive` | O app não está no ar. Faça o Lab 07: `lab 07` e depois `./deploy_gcp.sh`. |
| `o app não está conectado ao AlloyDB` | Confira com `lab alloydb`. Se ele estiver pronto, publique o app de novo: `lab 07` e `./deploy_gcp.sh`. |
| O Studio recusa a senha | Copie de novo com `lab alloydb senha`, sem espaços no fim. O usuário é `postgres`. |
| `relation "auditops_vector_chunks" does not exist` | O app ainda não conectou ao banco, porque ele cria as tabelas na primeira conexão. Rode `python verificar.py` antes. |
| A consulta 3.3 não devolve nada | Ainda não há trechos com vetor. Rode `python verificar.py` para fazer uma auditoria e tente de novo. |
| `lab alloydb` mostra um erro de rede | O projeto não tem a rede `default`. Peça à infra o nome da rede e rode `export VPC_NETWORK=<rede>` e `export VPC_SUBNET=<sub-rede>` antes do `lab alloydb`. |

## Fim

Você construiu um agente, deu a ele saída estruturada, uma ferramenta de busca, colegas especialistas, um roteamento de modelos por custo e proteção contra manipulação. Depois publicou tudo como um produto e viu o banco vetorial por dentro.

O mesmo caminho serve para outros documentos da sua empresa: notas fiscais, apólices, editais, laudos. Troque as instruções, o schema e as políticas, e mantenha a arquitetura.

Não esqueça do `lab limpar`.
