#!/usr/bin/env bash
# Instala la llave publica del PC de Fernando en este servidor para poder desplegar por
# SSH sin depender de la consola VNC, y despliega. Creado 2026-09-02.
# La llave PUBLICA no es secreta: solo autoriza entrar, no permite hacerse pasar por nadie.
# Idempotente: si ya esta, no la duplica.
set -uo pipefail

LLAVE='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKfNKnHLt0pXYKyvVzw6kwlzFj2BaUX3oMXSW3m+mu63 micartera-deploy-pc-windows-2026-09-02'
MARCA='micartera-deploy-pc-windows-2026-09-02'

mkdir -p ~/.ssh && chmod 700 ~/.ssh
if grep -qF "$MARCA" ~/.ssh/authorized_keys 2>/dev/null; then
  echo "LLAVE ya estaba instalada"
else
  echo "$LLAVE" >> ~/.ssh/authorized_keys
  echo "LLAVE_INSTALADA"
fi
chmod 600 ~/.ssh/authorized_keys

echo "--- desplegando ---"
D="$HOME/servicios/beneficios-bancarios-chile"
cd "$D" || { echo "no existe $D"; exit 1; }
if [ -f deploy_vps.sh ]; then
  bash deploy_vps.sh
else
  git pull --ff-only && systemctl --user restart cartera.service && echo "reiniciado (deploy_vps.sh aun no estaba, se uso el metodo manual)"
fi
