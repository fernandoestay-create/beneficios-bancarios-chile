#!/usr/bin/env bash
# Despliegue de MiCartera en el VPS — pull + restart + VERIFICACIÓN.
#
# Por qué existe (L-44): el `git pull` SOLO no despliega nada. La app carga
# beneficios.json / beneficios_otros.json / bencinas.json / cuotas en MEMORIA al
# bootear, así que sin `restart` el servicio sigue sirviendo la data que cargó la
# última vez que arrancó. Eso dejó producción 3 días congelada (2026-09-02) sirviendo
# 903 beneficios del 30-ago mientras el repo ya tenía los del 1-sep.
#
# Y por la regla cardinal del workspace ("¿corrió?" no es "¿insertó?", aquí
# "¿pusheó?" no es "¿está sirviendo?"), este script NO se da por bueno con un exit 0
# del restart: vuelve a preguntarle a producción de cuándo es el dato que está
# sirviendo y falla si no quedó al día.
#
# Uso EN EL VPS:   bash ~/servicios/beneficios-bancarios-chile/deploy_vps.sh
# Cron sugerido (una vez al día, después del scrape de las 09:00 Chile):
#   30 14 * * * bash ~/servicios/beneficios-bancarios-chile/deploy_vps.sh >> ~/deploy_cartera.log 2>&1
set -uo pipefail

DIR="${CARTERA_DIR:-$HOME/servicios/beneficios-bancarios-chile}"
SERVICIO="${CARTERA_SERVICE:-cartera.service}"
URL="${PROD_URL:-https://datalab-api.duckdns.org}"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $*"; }

cd "$DIR" || { log "ERROR: no existe $DIR"; exit 1; }

log "===== Deploy MiCartera ====="
ANTES="$(git rev-parse --short HEAD)"
git pull --ff-only || { log "ERROR: git pull falló (¿cambios locales sin commitear en el VPS?)"; exit 1; }
DESPUES="$(git rev-parse --short HEAD)"
log "commit $ANTES -> $DESPUES"

# El restart va SIEMPRE, incluso sin commits nuevos: el cron del scraper commitea los
# JSON de datos, y esos solo llegan al usuario cuando el proceso los vuelve a leer.
systemctl --user restart "$SERVICIO" || { log "ERROR: no se pudo reiniciar $SERVICIO"; exit 1; }
log "servicio reiniciado, esperando que levante..."
sleep 12

# ── Verificación: ¿qué está sirviendo REALMENTE? ──────────────────────────────
EST="$(curl -sS -m 30 -A 'curl/8.4.0' "$URL/estadisticas" 2>/dev/null)"
if [ -z "$EST" ]; then
  log "ERROR: $URL/estadisticas no responde tras el restart — REVISAR: journalctl --user -u $SERVICIO -n 50"
  exit 1
fi

leer() { printf '%s' "$EST" | python3 -c "import sys,json;print(json.load(sys.stdin).get('$1') or '')" 2>/dev/null; }
SIRVE_COMMIT="$(leer version_commit)"
SIRVE_FECHA="$(leer fecha_datos)"
SIRVE_TOTAL="$(leer total_beneficios)"

REPO_FECHA="$(python3 -c "
import json
d=json.load(open('beneficios.json',encoding='utf-8'))
f=[b.get('fecha_scrape') for b in d if b.get('fecha_scrape')]
print(max(f) if f else '')" 2>/dev/null)"

log "sirviendo: commit=${SIRVE_COMMIT:-?} datos=${SIRVE_FECHA:0:10} total=${SIRVE_TOTAL:-?}"
log "repo:      commit=$DESPUES datos=${REPO_FECHA:0:10}"

if [ -z "$SIRVE_FECHA" ]; then
  log "AVISO: producción no expone 'fecha_datos' — quedó corriendo código anterior al fix L-44."
  exit 1
fi
if [ "${SIRVE_FECHA:0:10}" != "${REPO_FECHA:0:10}" ]; then
  log "ERROR: el restart NO tomó los datos nuevos (sirve ${SIRVE_FECHA:0:10}, repo ${REPO_FECHA:0:10})."
  exit 1
fi

log "===== Deploy OK — producción sirviendo el commit $DESPUES ====="
