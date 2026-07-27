/**
 * Lanzador multiplataforma de la suite de QA (`npm test`).
 * Misma razon de ser que `dev-backend.mjs`: resolver el interprete del
 * entorno virtual segun el sistema operativo.
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

// Los argumentos extra se reenvian a pytest: `npm test -- -k validacion`
const extra = process.argv.slice(2)

// Sin ruta explicita: `pytest.ini` ya apunta a `backend/tests`.
const proceso = spawn(python, ['-m', 'pytest', ...extra], {
  cwd: RAIZ,
  stdio: 'inherit',
  shell: false,
})

proceso.on('exit', (codigo) => process.exit(codigo ?? 0))
proceso.on('error', (error) => {
  console.error('[AthenIA] No se pudo ejecutar pytest:', error.message)
  process.exit(1)
})
