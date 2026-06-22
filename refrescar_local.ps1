# ============================================================
#  refrescar_local.ps1  --  Refresco de MiCartera desde Chile
# ============================================================
#  Scrapea los 15 bancos desde tu IP local (Chile, SIN geo-fence),
#  corre el chequeo experto por banco y actualiza produccion.
#  Pensado para correr a mano o como Tarea Programada de Windows ($0).
#
#  Resuelve AUTOMATICAMENTE, para TODOS los bancos:
#    - geo-fence por IP (ej. Falabella, que el cron USA no puede traer)
#    - fallas transitorias (reintentos del propio scrapers.py)
#  Si un banco cae por CAMBIO DE ESTRUCTURA de su web, NO lo toca (eso
#  necesita arreglo de codigo) pero: deja sus datos previos (no desaparece
#  de la web) y guarda su HTML crudo en diagnostico\ para arreglarlo rapido.
#
#  Uso manual:   powershell -ExecutionPolicy Bypass -File refrescar_local.ps1
#  Automatico:   ver INSTALAR_TAREA al final de este archivo.
# ============================================================
$ErrorActionPreference = "Stop"
$CLONE = "$env:USERPROFILE\micartera-clone"
$VENV  = "$env:USERPROFILE\.venvs\micartera_win"
$PY    = "$VENV\Scripts\python.exe"
$REPO  = "https://github.com/fernandoestay-create/beneficios-bancarios-chile.git"
$LOG   = "$env:USERPROFILE\micartera_refresco.log"

function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $m" | Tee-Object -FilePath $LOG -Append }

Log "===== Inicio refresco local (Chile) ====="

# 1. Clone local como fuente de verdad de git (el .git de Drive es inestable)
if (-not (Test-Path "$CLONE\.git")) { git clone $REPO $CLONE | Out-Null }
git -C $CLONE fetch origin --quiet
git -C $CLONE reset --hard origin/main --quiet
Log "Repo sincronizado a origin/main"

# 2. venv + dependencias minimas del scraper
if (-not (Test-Path $PY)) { python -m venv $VENV }
& $PY -m pip install -q requests beautifulsoup4 lxml
Log "Entorno Python listo"

# 3. Scrapear los 15 desde Chile + chequeo experto + red de seguridad + reporte
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
Push-Location $CLONE
& $PY scrapers.py
Log "Scrape de los 15 bancos completo"

# 4. Health check: gate duro, NO se pushea data mala
& $PY verificar_salud.py
if ($LASTEXITCODE -ne 0) { Log "HEALTH CHECK FALLO -- no se pushea"; Pop-Location; exit 1 }
Log "Health check OK"

# 5. Diagnostico de bancos caidos: guarda su HTML en diagnostico\ (arreglo rapido)
& $PY diagnosticar.py --desde-status

# 6. Commit + push si hay cambios -> Render redeploya con la data fresca
git -C $CLONE add beneficios.json beneficios.csv bencinas.json
git -C $CLONE diff --staged --quiet
if ($LASTEXITCODE -ne 0) {
    git -C $CLONE commit -m "Refresco local (Chile) $(Get-Date -Format yyyy-MM-dd)" --quiet
    git -C $CLONE push --quiet
    Log "Produccion actualizada (push hecho)"
} else {
    Log "Sin cambios que pushear (produccion ya estaba al dia)"
}
Pop-Location
Log "===== Fin refresco ====="

# 7. Abrir el reporte por banco (para revisarlos todos de un vistazo)
if (Test-Path "$CLONE\reporte_email.html") { Start-Process "$CLONE\reporte_email.html" }

# ============================================================
#  INSTALAR_TAREA  (correr UNA vez, en PowerShell, para automatizar)
#  Corre todos los dias a las 09:00. Cambia /SC y /ST a gusto.
#
#  $script = "$env:USERPROFILE\micartera-clone\refrescar_local.ps1"
#  schtasks /Create /TN "MiCartera-Refresco" /TR "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`"" /SC DAILY /ST 09:00 /F
#
#  Ver:      schtasks /Query /TN "MiCartera-Refresco"
#  Correr:   schtasks /Run   /TN "MiCartera-Refresco"
#  Borrar:   schtasks /Delete /TN "MiCartera-Refresco" /F
# ============================================================
