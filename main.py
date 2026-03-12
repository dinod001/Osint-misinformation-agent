import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

import time
import json
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.chat_service.cag_service import CAGService
from infrastructure.llm.vision_provider import vision_provider

app = FastAPI(
    title="OSINT Misinformation Detector",
    description="AI-powered real-time fake news & war misinformation detection",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize the CAG service once on startup
cag_service = CAGService()

class ClaimRequest(BaseModel):
    claim: str

class VerifyResponse(BaseModel):
    verdict: str
    confidence_score: str
    explanation: str
    top_sources: list[str]
    cached: bool
    latency_ms: int

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/verify", response_model=VerifyResponse)
async def verify_claim(request: ClaimRequest):
    if not request.claim or len(request.claim.strip()) < 5:
        raise HTTPException(status_code=400, detail="Claim is too short.")

    start = time.perf_counter()

    # Let the CAG service handle cache check + full pipeline internally
    result = cag_service.generate(request.claim, use_cache=True)
    latency_ms = int((time.perf_counter() - start) * 1000)

    if not result:
        raise HTTPException(status_code=500, detail="Failed to verify claim.")

    # Parse result if it's a string (raw LLM output fallback)
    if isinstance(result, str):
        try:
            result = json.loads(result.strip().strip("```json").strip("```"))
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to parse LLM response.")

    # 'score' key only present on cache hits (from cag_cache.get())
    was_cached = "score" in result

    return VerifyResponse(
        verdict=result.get("verdict", "UNVERIFIED"),
        confidence_score=result.get("confidence_score", "0%"),
        explanation=result.get("explanation", ""),
        top_sources=result.get("top_sources", []),
        cached=was_cached,
        latency_ms=latency_ms
    )

@app.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    
    try:
        contents = await file.read()
        claim = vision_provider.extract_claim(contents)
        
        if not claim:
            raise HTTPException(status_code=400, detail="Could not identify a claim in this image.")
            
        return {"claim": claim}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")

@app.get("/health")
async def health():
    return {"status": "operational", "service": "OSINT Misinformation Detector"}
