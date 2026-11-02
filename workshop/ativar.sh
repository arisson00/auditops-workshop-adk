# Prepara (só na primeira vez) e ativa o ambiente Python do workshop.
# Uso, de qualquer pasta:  source ~/auditops-workshop-adk/workshop/ativar.sh

WORKSHOP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# O marcador só é criado depois que a instalação termina: se ela falhar no meio, roda de novo
if [ ! -f "$WORKSHOP_DIR/.venv/.instalado" ]; then
  echo "Preparando o ambiente Python do workshop (só na primeira vez, 1 a 2 minutos)..."
  if python3 -m venv "$WORKSHOP_DIR/.venv" \
      && "$WORKSHOP_DIR/.venv/bin/pip" install -q --disable-pip-version-check -r "$WORKSHOP_DIR/requirements.txt"; then
    touch "$WORKSHOP_DIR/.venv/.instalado"
  else
    echo "ERRO: a instalação falhou (veja a mensagem acima). Rode o mesmo comando de novo."
    return 1 2>/dev/null || exit 1
  fi
fi

source "$WORKSHOP_DIR/.venv/bin/activate"
echo "✓ ambiente do workshop ativo ($(python -c 'import google.adk; print("google-adk", google.adk.__version__)'))"
