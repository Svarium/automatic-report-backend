import sys
import os
from pathlib import Path

# Fix para empaquetado: Asegurar que el directorio raíz esté en el path
# Esto permite que 'from app.xxx' funcione en cualquier entorno empaquetado
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.analyzer import analyze_report

app = FastAPI(
    title="School Report Analyzer",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los headers
)


@app.get("/health")
async def health():
    """Endpoint de health check para que Electron detecte cuando el backend está listo"""
    return {"status": "ok"}


@app.post("/analyze-report")
async def analyze(file: UploadFile = File(...)):
    if not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Formato no soportado")

    try:
        result = analyze_report(file)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Iniciar uvicorn cuando se ejecuta directamente (no cuando se importa)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
