from fastapi import FastAPI, UploadFile, File, HTTPException
from app.analyzer import analyze_report

app = FastAPI(
    title="School Report Analyzer",
    version="1.0.0"
)


@app.post("/analyze-report")
async def analyze(file: UploadFile = File(...)):
    if not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Formato no soportado")

    try:
        result = analyze_report(file)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
