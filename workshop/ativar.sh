# Prepara o workshop e cria o comando `lab`. Rode uma vez, depois do git clone:
#     source auditops-workshop-adk/workshop/ativar.sh
#
# Depois, em qualquer pasta e mesmo após o Cloud Shell reiniciar:
#     lab 01            entra no starter do Lab 01, com o ambiente e o projeto GCP prontos
#     lab 01 solucao    entra na solução do Lab 01
#     lab 07            vai para a raiz do repositório (deploy)
#     lab web           abre a interface do ADK (adk web) para o lab da pasta atual

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

lab() {
  local numero="${1:-}" pasta="${2:-starter}" projeto destino pacote
  if [ -z "$numero" ]; then
    echo "Uso: lab <número> [solucao]   |   lab web     ex.: lab 01   |   lab 03 solucao"
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
    # A Visualização da Web do Cloud Shell abre a página em https://8080-....cloudshell.dev.
    # O adk web só aceita a própria máquina como origem; sem liberar o Cloud Shell, os
    # arquivos .js da interface voltam 403 e a página fica em branco
    # Um adk web esquecido (outra aba, ou pausado com Ctrl+Z) prende a porta 8080: encerra antes.
    # O "[b]" faz o padrão casar só com o processo do ADK, nunca com um shell que contenha este texto
    if pkill -f "[b]in/adk web --port 8080" 2>/dev/null; then
      # Um processo pausado com Ctrl+Z só recebe o pedido de encerrar depois de retomado
      pkill -CONT -f "[b]in/adk web --port 8080" 2>/dev/null
      echo "→ encerrei um adk web que já estava aberto"
      sleep 2
    fi
    if (exec 3<>/dev/tcp/127.0.0.1/8080) 2>/dev/null; then
      echo "✗ outro programa está usando a porta 8080. Veja qual com: lsof -i :8080"
      return 1
    fi
    echo "→ abra pela Visualização da Web do Cloud Shell, porta 8080. Para parar: Ctrl+C"
    adk web --port 8080 --allow_origins 'regex:https://.*\.cloudshell\.dev'
    return
  fi
  if [ "$numero" = "07" ] || [ "$numero" = "7" ]; then
    cd "$AUDITOPS_WORKSHOP/.." && echo "✓ raiz do repositório: $(pwd)"
    return
  fi
  destino="$(ls -d "$AUDITOPS_WORKSHOP"/labs/"$(printf '%02d' "$((10#$numero))")"-*/"$pasta" 2>/dev/null | head -1)"
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
  echo "✓ $(basename "$(dirname "$destino")")/$pasta   |   projeto: $projeto"
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
