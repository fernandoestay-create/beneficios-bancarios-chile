# ============================================================
#  refrescar_local.ps1  --  Refresco de MiCartera desde Chile
# ============================================================
#  Scrapea los 15 bancos desde tu IP local (Chile, SIN geo-fence),
#  corre el chequeo experto por banco, actualiza produccion y TE MANDA
#  UN MAIL "por si o por no" (verde si todo OK, rojo si algo fallo).
#  Pensado para correr a mano o como Tarea Programada de Windows ($0).
#
#  Resuelve AUTOMATICAMENTE, para TODOS los bancos: geo-fence por IP
#  (ej. Falabella) + fallas transitorias. Si un banco cae por cambio de
#  estructura, NO lo toca (deja sus datos previos, no desaparece de la web)
#  y guarda su HTML en diagnostico\ para arreglo rapido.
#
#  Para el MAIL necesita 2 variables de entorno (una sola vez, ver INSTALAR_MAIL):
#     GMAIL_USER           (tu correo Gmail remitente)
#     GMAIL_APP_PASSWORD   (app password de Gmail, 16 letras)
#  Sin esas variables el refresco igual corre y actualiza; solo no manda mail.
#
#  Uso manual:   powershell -ExecutionPolicy Bypass -File refrescar_local.ps1
#  Automatico:   ver INSTALAR_TAREA al final de este archivo.
# ============================================================
$CLONE = "$env:USERPROFILE\micartera-clone"
$VENV  = "$env:USERPROFILE\.venvs\micartera_win"
$PY    = "$VENV\Scripts\python.exe"
$REPO  = "https://github.com/fernandoestay-create/beneficios-bancarios-chile.git"
$LOG   = "$env:USERPROFILE\micartera_refresco.log"
$DEST  = "fernando.estay@gmail.com"

function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $m" | Tee-Object -FilePath $LOG -Append }

function Enviar-Mail($asunto, $cuerpoHtml) {
    $user = $env:GMAIL_USER; $pass = $env:GMAIL_APP_PASSWORD
    if (-not $user -or -not $pass) { Log "Sin GMAIL_USER/GMAIL_APP_PASSWORD: no se manda mail (config: ver INSTALAR_MAIL)"; return }
    try {
        $sec = ConvertTo-SecureString $pass -AsPlainText -Force
        $cred = New-Object System.Management.Automation.PSCredential($user, $sec)
        Send-MailMessage -From $user -To $DEST -Subject $asunto -Body $cuerpoHtml -BodyAsHtml `
            -SmtpServer "smtp.gmail.com" -Port 587 -UseSsl -Credential $cred -Encoding ([System.Text.Encoding]::UTF8) -ErrorAction Stop
        Log "Mail enviado: $asunto"
    } catch { Log "Error enviando mail: $($_.Exception.Message)" }
}

Log "===== Inicio refresco local (Chile) ====="
$asunto = ""; $cuerpo = ""

try {
    # 1. Clone local como fuente de verdad de git (el .git de Drive es inestable)
    if (-not (Test-Path "$CLONE\.git")) { git clone $REPO $CLONE | Out-Null }
    git -C $CLONE fetch origin --quiet
    git -C $CLONE reset --hard origin/main --quiet
    Log "Repo sincronizado a origin/main"

    # 2. venv + dependencias minimas del scraper
    if (-not (Test-Path $PY)) { python -m venv $VENV }
    & $PY -m pip install -q requests beautifulsoup4 lxml
    Log "Entorno Python listo"

    # 3. Scrape de los 15 desde Chile + chequeo experto + red de seguridad + reporte
    $env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"
    Push-Location $CLONE
    & $PY scrapers.py
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw "scrapers.py fallo (exit $LASTEXITCODE)" }
    Log "Scrape de los 15 bancos completo"

    # 4. Health check: gate duro, NO se pushea data mala
    & $PY verificar_salud.py
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Health check FALLO (no se pushea)" }
    Log "Health check OK"

    # 5. Diagnostico de bancos caidos: guarda su HTML para arreglo rapido
    & $PY diagnosticar.py --desde-status

    # 6. Commit + push si hay cambios -> Render redeploya
    git -C $CLONE add beneficios.json beneficios.csv bencinas.json
    git -C $CLONE diff --staged --quiet
    if ($LASTEXITCODE -ne 0) {
        git -C $CLONE commit -m "Refresco local (Chile) $(Get-Date -Format yyyy-MM-dd)" --quiet
        git -C $CLONE push --quiet
        Log "Produccion actualizada (push hecho)"
    } else { Log "Sin cambios que pushear (produccion ya estaba al dia)" }
    Pop-Location

    # 7. Armar el mail con el reporte por banco que genero scrapers.py
    $asunto = (Get-Content "$CLONE\asunto_email.txt" -Raw -Encoding UTF8).Trim()
    $cuerpo = Get-Content "$CLONE\reporte_email.html" -Raw -Encoding UTF8
    Log "===== Fin refresco OK ====="
}
catch {
    $asunto = "X Refresco local MiCartera FALLO - $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    $cuerpo = "<div style='font-family:Arial'><h2 style='color:#dc2626'>El refresco local fallo</h2>" +
              "<p><b>Motivo:</b> $($_.Exception.Message)</p>" +
              "<p>La web sigue con los datos anteriores (no se pusheo data mala). Revisa el log:</p>" +
              "<pre style='background:#f3f4f6;padding:10px;font-size:12px'>$LOG</pre></div>"
    Log "FALLO: $($_.Exception.Message)"
}

# Mail SIEMPRE (por si o por no) — confirmacion de que el refresco corrio
Enviar-Mail $asunto $cuerpo

# ============================================================
#  INSTALAR_MAIL  (correr UNA vez en PowerShell, para activar el correo)
#  Reusa el mismo app password de Gmail que ya tienes en GitHub Secrets.
#
#  setx GMAIL_USER "tucorreo@gmail.com"
#  setx GMAIL_APP_PASSWORD "xxxxxxxxxxxxxxxx"
#  (cierra y reabre PowerShell para que tomen efecto)
#
#  INSTALAR_TAREA  (correr UNA vez, para automatizar diario 09:00)
#  $s = "$env:USERPROFILE\micartera-clone\refrescar_local.ps1"
#  schtasks /Create /TN "MiCartera-Refresco" /TR "powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$s`"" /SC DAILY /ST 09:00 /F
#
#  Ver: schtasks /Query /TN "MiCartera-Refresco"  | Correr ya: schtasks /Run /TN "MiCartera-Refresco"
# ============================================================
