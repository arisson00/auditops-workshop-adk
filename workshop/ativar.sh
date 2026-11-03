# Prepara o workshop e cria o comando `lab`. Rode uma vez, depois do git clone:
#     source auditops-workshop-adk/workshop/ativar.sh
#
# Depois, em qualquer pasta e mesmo após o Cloud Shell reiniciar:
#     lab 01            entra no starter do Lab 01, com o ambiente e o projeto GCP prontos
#     lab 01 solucao    entra na solução do Lab 01
#     lab 07            vai para a raiz do repositório (deploy)
#     lab web           abre a interface do ADK (adk web) para o lab da pasta atual
#     lab app           abre o AuditOps publicado no Cloud Run (lab 07), mesmo sem acesso público
#     lab alloydb       cria o AlloyDB em segundo plano (ou confere o que a infra criou); lab alloydb senha
#     lab limpar        apaga o que o workshop criou no projeto, para não gerar custo

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  echo "Use com source, não com bash:  source ${0}"
  exit 1
fi

AUDITOPS_WORKSHOP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AUDITOPS_WORKSHOP

# Projeto GCP: o que estiver selecionado no gcloud (no Cloud Shell, o projeto escolhido no console)
_auditops_projeto() {
  gcloud config get-value project 2>/dev/null
}

# Libera a porta 8080 e mostra o link da Visualização da Web do Cloud Shell
_auditops_preparar_porta() {
  # Um adk web ou um túnel esquecido (outra aba, ou pausado com Ctrl+Z) prende a porta: encerra antes.
  # Os padrões miram o processo do ADK, o do gcloud que abre o túnel e o binário do túnel. O "[b]",
  # "[g]" e "[c]" fazem o padrão não casar com o próprio texto dele, num shell que o contenha
  local padrao
  for padrao in "[b]in/adk web --port 8080" "[g]cloud.py run services proxy" "[c]loud-run-proxy"; do
    if pkill -f "$padrao" 2>/dev/null; then
      # Um processo pausado com Ctrl+Z só recebe o pedido de encerrar depois de retomado
      pkill -CONT -f "$padrao" 2>/dev/null
      echo "→ encerrei um processo antigo que ocupava a porta 8080"
      sleep 2
    fi
  done
  if (exec 3<>/dev/tcp/127.0.0.1/8080) 2>/dev/null; then
    echo "✗ outro programa está usando a porta 8080. Veja qual com: lsof -i :8080"
    return 1
  fi
  # O endereço 127.0.0.1 é o da máquina do Cloud Shell, não o do seu computador
  local url
  url="$(cloudshell get-web-preview-url -p 8080 2>/dev/null)"
  echo "──────────────────────────────────────────────────────────────────────────"
  if [ -n "$url" ]; then
    echo " Abra no navegador:  $url"
  else
    echo " No topo do Cloud Shell: Visualização da Web > Visualizar na porta 8080"
  fi
  echo " Não use endereços http://127.0.0.1:8080 que aparecerem abaixo. Para parar: Ctrl+C"
  echo "──────────────────────────────────────────────────────────────────────────"
}

lab() {
  local numero="${1:-}" pasta="${2:-starter}" projeto destino pacote
  if [ -z "$numero" ]; then
    echo "Uso: lab <número> [solucao]  |  lab web  |  lab app  |  lab alloydb  |  lab limpar     ex.: lab 01"
    ls -1 "$AUDITOPS_WORKSHOP/labs"
    return 1
  fi
  if [ ! -f "$AUDITOPS_WORKSHOP/.venv/.instalado" ]; then
    echo "✗ o workshop ainda não foi preparado. Rode: source $AUDITOPS_WORKSHOP/ativar.sh"
    return 1
  fi
  source "$AUDITOPS_WORKSHOP/.venv/bin/activate"
  if [ "$numero" = "web" ]; then
    if ! ls */agent.py >/dev/null 2>&1; then
      echo "✗ nenhum agente nesta pasta. Entre no lab antes, ex.: lab 01"
      return 1
    fi
    _auditops_preparar_porta || return 1
    # A Visualização da Web do Cloud Shell abre a página em https://8080-....cloudshell.dev.
    # O adk web só aceita a própria máquina como origem; sem liberar o Cloud Shell, os
    # arquivos .js da interface voltam 403 e a página fica em branco
    adk web --port 8080 --allow_origins 'regex:https://.*\.cloudshell\.dev'
    return
  fi
  if [ "$numero" = "alloydb" ]; then
    local cluster="${ALLOYDB_CLUSTER:-auditops-alloydb-cluster}" instancia="${ALLOYDB_INSTANCE:-auditops-alloydb-primary}"
    local segredo="${ALLOYDB_SECRET:-auditops-alloydb-password}" regiao="${GOOGLE_CLOUD_LOCATION:-us-central1}" estado
    local log="$HOME/auditops-alloydb.log" marcador="$HOME/.auditops-alloydb-criado-por-mim"
    if [ "$pasta" = "senha" ]; then
      # A senha do usuário postgres, para entrar no AlloyDB Studio (lab 08)
      gcloud secrets versions access latest --secret "$segredo" && echo
      return
    fi
    if pgrep -f "[s]etup_alloydb.sh" >/dev/null; then
      echo "→ o AlloyDB está sendo criado (leva de 25 a 35 minutos). Última linha do log:"
      tail -1 "$log"
      echo "  Continue com os labs. Para o log completo: tail -f ~/auditops-alloydb.log"
      return
    fi
    estado="$(gcloud alloydb instances describe "$instancia" --cluster "$cluster" --region "$regiao" --format='value(state)' 2>/dev/null)"
    if [ "$estado" = "READY" ]; then
      echo "✓ AlloyDB pronto: $cluster / $instancia"
      if [ -f "$marcador" ]; then
        echo "  Criado por você neste workshop: ele cobra por hora. No fim, rode lab limpar."
      else
        echo "  Ele já existia no projeto (em geral, criado pela infra). O lab limpar não vai apagá-lo."
      fi
      return
    fi
    if [ -n "$estado" ]; then
      echo "→ a instância do AlloyDB existe, mas está no estado $estado. Rode lab alloydb de novo em alguns minutos."
      return
    fi
    # Não existe e ninguém está criando: cria em segundo plano. O script retoma de onde parou se for interrompido
    if ! gcloud alloydb clusters describe "$cluster" --region "$regiao" >/dev/null 2>&1; then
      touch "$marcador"
    fi
    if [ -s "$log" ] && grep -q "ERRO" "$log"; then
      echo "! a última tentativa terminou com erro:"; grep "ERRO" -A2 "$log" | head -4
      echo "  Tentando de novo..."
    fi
    echo "→ criando o AlloyDB em segundo plano (leva de 25 a 35 minutos)."
    (cd "$AUDITOPS_WORKSHOP/.." && nohup ./setup_alloydb.sh > "$log" 2>&1 &)
    echo "  Pode continuar com os labs. Para ver o andamento: lab alloydb"
    echo "  Se o Cloud Shell fechar, rode lab alloydb de novo: ele continua de onde parou."
    return
  fi
  if [ "$numero" = "limpar" ]; then
    # Encerra o que estiver rodando no Cloud Shell e apaga o que o workshop criou no projeto.
    # O AlloyDB só é apagado se foi criado neste workshop (lab alloydb); o da infra fica
    pkill -f "[b]in/adk web --port 8080" 2>/dev/null
    pkill -f "[g]cloud.py run services proxy" 2>/dev/null
    local marcador="$HOME/.auditops-alloydb-criado-por-mim"
    if pgrep -f "[s]etup_alloydb.sh" >/dev/null; then
      echo "✗ o AlloyDB ainda está sendo criado. Espere terminar (lab alloydb) e rode lab limpar de novo."
      return 1
    fi
    if [ -f "$marcador" ]; then
      (cd "$AUDITOPS_WORKSHOP/.." && ./cleanup_gcp.sh) && \
        ! gcloud alloydb clusters describe "${ALLOYDB_CLUSTER:-auditops-alloydb-cluster}" \
            --region "${GOOGLE_CLOUD_LOCATION:-us-central1}" >/dev/null 2>&1 && rm -f "$marcador"
    else
      echo "→ o AlloyDB não foi criado por você neste workshop: apago só o app e a imagem dele."
      (cd "$AUDITOPS_WORKSHOP/.." && ./cleanup_gcp.sh --so-app)
    fi
    return
  fi
  if [ "$numero" = "app" ]; then
    local servico="${SERVICE_NAME:-auditops-executive}" regiao="${GOOGLE_CLOUD_LOCATION:-us-central1}" url_app codigo
    url_app="$(gcloud run services describe "$servico" --region "$regiao" --format='value(status.url)' 2>/dev/null)"
    if [ -z "$url_app" ]; then
      echo "✗ não achei o serviço $servico em $regiao. Faça o deploy antes: lab 07 e depois ./deploy_gcp.sh"
      return 1
    fi
    codigo="$(curl -s -o /dev/null -w '%{http_code}' "$url_app/" 2>/dev/null)"
    if [ "$codigo" = "200" ]; then
      echo "✓ o AuditOps está aberto ao público. Abra direto no navegador: $url_app"
      return
    fi
    # Acesso público bloqueado (em geral, política da organização que proíbe allUsers):
    # o túnel abre o app pela Visualização da Web, autenticado com o seu login do Cloud Shell
    echo "→ o acesso público ao app está bloqueado (HTTP $codigo). Abrindo um túnel com o seu login..."
    _auditops_preparar_porta || return 1
    gcloud run services proxy "$servico" --region "$regiao" --port 8080
    return
  fi
  if [ "$numero" = "07" ] || [ "$numero" = "7" ]; then
    cd "$AUDITOPS_WORKSHOP/.." && echo "✓ raiz do repositório: $(pwd)"
    return
  fi
  destino="$(ls -d "$AUDITOPS_WORKSHOP"/labs/"$(printf '%02d' "$((10#$numero))")"-*/"$pasta" 2>/dev/null | head -1)"
  # Labs de exploração (ex.: 08) não têm starter/: entra na pasta do próprio lab
  if [ -z "$destino" ] && [ "$pasta" = "starter" ]; then
    destino="$(ls -d "$AUDITOPS_WORKSHOP"/labs/"$(printf '%02d' "$((10#$numero))")"-*/ 2>/dev/null | head -1)"
    destino="${destino%/}"
    [ -n "$destino" ] && pasta=""
  fi
  if [ -z "$destino" ]; then
    echo "✗ não achei o lab $numero/$pasta. Os labs são:"; ls -1 "$AUDITOPS_WORKSHOP/labs"
    return 1
  fi
  projeto="$(_auditops_projeto)"
  if [ -z "$projeto" ]; then
    echo "✗ nenhum projeto GCP selecionado. Rode: gcloud config set project <SEU_PROJECT_ID>"
    return 1
  fi
  cd "$destino" || return 1
  # O .env é refeito a cada vez com o projeto atual: trocar de conta ou de projeto não quebra nada
  for pacote in */; do
    [ -f "$pacote/agent.py" ] || continue
    printf 'GOOGLE_GENAI_USE_VERTEXAI=TRUE\nGOOGLE_CLOUD_PROJECT=%s\nGOOGLE_CLOUD_LOCATION=global\n' "$projeto" > "$pacote/.env"
  done
  if [ -n "$pasta" ]; then
    echo "✓ $(basename "$(dirname "$destino")")/$pasta   |   projeto: $projeto"
  else
    echo "✓ $(basename "$destino")   |   projeto: $projeto"
  fi
}

# Nos terminais seguintes (chamado pelo ~/.bashrc), só define o comando `lab`, sem demora
if [ -n "${AUDITOPS_SO_COMANDO:-}" ]; then
  return 0
fi

# 1. Projeto GCP
if [ -z "$(_auditops_projeto)" ]; then
  echo "✗ nenhum projeto GCP selecionado. Rode: gcloud config set project <SEU_PROJECT_ID>"
  echo "  e depois este mesmo comando de novo."
  return 1
fi

# 2. Ambiente Python e API do Vertex AI, só na primeira vez. O marcador só é criado se tudo terminar
if [ ! -f "$AUDITOPS_WORKSHOP/.venv/.instalado" ]; then
  echo "→ instalando o Google ADK (só na primeira vez, 1 a 2 minutos)..."
  if ! python3 -m venv "$AUDITOPS_WORKSHOP/.venv" \
      || ! "$AUDITOPS_WORKSHOP/.venv/bin/pip" install -q --disable-pip-version-check -r "$AUDITOPS_WORKSHOP/requirements.txt"; then
    echo "✗ a instalação falhou (veja a mensagem acima). Rode o mesmo comando de novo."
    return 1
  fi
  echo "→ ativando a API do Vertex AI no projeto $(_auditops_projeto)..."
  gcloud services enable aiplatform.googleapis.com --quiet \
    || echo "  Aviso: não consegui ativar a API (sem permissão?). Peça a quem administra o projeto."
  touch "$AUDITOPS_WORKSHOP/.venv/.instalado"
fi

# 3. Deixa o comando `lab` disponível nos próximos terminais e após o Cloud Shell reiniciar
if ! grep -q "auditops-workshop >>>" ~/.bashrc 2>/dev/null; then
  printf '\n# auditops-workshop >>>\n[ -f "%s/ativar.sh" ] && AUDITOPS_SO_COMANDO=1 source "%s/ativar.sh"\n# <<< auditops-workshop\n' \
    "$AUDITOPS_WORKSHOP" "$AUDITOPS_WORKSHOP" >> ~/.bashrc
fi

source "$AUDITOPS_WORKSHOP/.venv/bin/activate"
echo "✓ workshop pronto no projeto $(_auditops_projeto). Para começar: lab 01"
