/**
 * Lanzador multiplataforma del backend de AthenIA.
 *
 * Existe porque la ruta al interprete del entorno virtual cambia segun el SO
 * (`.venv/Scripts/python.exe` en Windows, `.venv/bin/python` en macOS/Linux) y
 * porque cmd.exe no acepta rutas relativas con "/". Asi el equipo corre
 * `npm run dev` igual en cualquier maquina.
 *
 * Si no encuentra el entorno virtual, cae al `python` del PATH.
 *
 * HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE
 * ---------------------------------------
 * `sentence-transformers` revalida el modelo de embeddings contra Hugging
 * Face en CADA arranque -unas 10 peticiones HTTP (~20-25s)- aunque el modelo
 * ya este cacheado localmente (ver `backend/scripts/precargar_modelo.py`).
 * Con la cache ya tibia, esas peticiones no aportan nada salvo latencia y un
 * punto de fallo mas si la red esta lenta o caida. Por eso este lanzador fija
 * ambas variables a "1" por defecto; una exportada a mano en la shell antes de
 * correr `npm run dev` tiene prioridad y las pisa.
 *
 * IMPORTANTE: correr `precargar_modelo.py` primero, SIN estas variables (asi
 * puede salir a red la primera vez). Si todavia no precargaste el modelo y
 * arrancas el backend directo, `/cursos` y `/cursos/buscar` van a fallar en
 * silencio con 0 resultados porque el modelo nunca se descarga en modo
 * offline.
 */
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const RAIZ = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const esWindows = process.platform === 'win32'

const pythonVenv = esWindows
  ? join(RAIZ, '.venv', 'Scripts', 'python.exe')
  : join(RAIZ, '.venv', 'bin', 'python')

const python = existsSync(pythonVenv) ? pythonVenv : esWindows ? 'python' : 'python3'

if (!existsSync(pythonVenv)) {
  console.warn(
    '[AthenIA] Entorno virtual no encontrado en .venv — usando el Python del PATH.\n' +
      '          Crea el entorno con:  python -m venv .venv',
  )
}

const proceso = spawn(
  python,
  ['-m', 'uvicorn', 'app.main:app', '--reload', '--port', '8000', '--host', '127.0.0.1'],
  {
    cwd: join(RAIZ, 'backend'),
    stdio: 'inherit',
    env: {
      ...process.env,
      HF_HUB_OFFLINE: process.env.HF_HUB_OFFLINE ?? '1',
      TRANSFORMERS_OFFLINE: process.env.TRANSFORMERS_OFFLINE ?? '1',
    },
    // En Windows, spawn de un .exe no necesita shell; evitarlo previene que
    // queden procesos huerfanos al detener `concurrently`.
    shell: false,
  },
)

proceso.on('exit', (codigo) => process.exit(codigo ?? 0))
proceso.on('error', (error) => {
  console.error('[AthenIA] No se pudo iniciar el backend:', error.message)
  process.exit(1)
})
