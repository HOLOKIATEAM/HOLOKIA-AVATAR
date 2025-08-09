import os
import stat
from fastapi import FastAPI, HTTPException, UploadFile, File # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from pydantic import BaseModel # type: ignore
import yaml
import io
import uuid
import subprocess
import json
import logging
from pydub import AudioSegment # type: ignore
import whisper # type: ignore
from fastapi.responses import FileResponse # type: ignore
import time
import hashlib
import platform
import tempfile

app = FastAPI(
    title="STT Server",
    description="API de reconnaissance vocale (Speech-to-Text)",
    version="1.0.0"
)

# Configurer CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurer les logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stt-server")

# Charger la configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "lipsync_config.yaml")
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        logger.info(f"Chargement du fichier de configuration : {os.path.abspath(f.name)}")
        config = yaml.safe_load(f)
except Exception as e:
    logger.error(f"Erreur lors de la lecture de lipsync_config.yaml : {str(e)}")
    config = {"languages": ["fr", "en", "ar"], "speakers": ["female-pt-4", "male-en-1"]}

LANGUAGES = config.get("languages", ["fr", "en", "ar"])
SPEAKERS = config.get("speakers", ["female-pt-4", "male-en-1"])
logger.info(f"Langues disponibles : {LANGUAGES}")
logger.info(f"Locuteurs disponibles : {SPEAKERS}")

# Dossier de sortie
OUTPUT_DIR = os.path.join(BASE_DIR, "../../lipsync-demo/public/audios")
os.makedirs(OUTPUT_DIR, exist_ok=True)
logger.info(f"Dossier de sortie : {OUTPUT_DIR}")

# Initialiser le modèle Whisper
try:
    model = whisper.load_model("base")
    logger.info("Modèle Whisper chargé avec succès")
except Exception as e:
    logger.error(f"Erreur lors du chargement du modèle Whisper : {e}")
    raise

class TranscriptionRequest(BaseModel):
    audio_id: str | None = None
    language: str | None = None

class TranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float | None = None

@app.get("/languages/")
async def get_languages():
    return {"languages": LANGUAGES}

@app.get("/speakers/")
async def get_speakers():
    return {"speakers": SPEAKERS}

@app.get("/health")
async def health_check():
    try:
        if not os.access(OUTPUT_DIR, os.W_OK):
            return {"status": "error", "message": "Dossier de sortie non accessible en écriture"}
        
        # Test du modèle Whisper
        try:
            test_result = model.transcribe("test_audio.wav", language="en")
            whisper_status = "available"
        except Exception as e:
            whisper_status = f"error: {str(e)}"
            
        return {
            "status": "healthy",
            "service": "STT Server",
            "version": "1.0.0",
            "languages": LANGUAGES,
            "whisper_status": whisper_status,
            "output_dir": OUTPUT_DIR,
            "timestamp": "2025-07-24T12:35:00Z"
        }
    except Exception as e:
        return {"status": "error", "message": f"Erreur interne : {str(e)}"}

@app.post("/transcribe/", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = None
):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Fichier audio requis")
        
        # Vérifier le type de fichier
        if not file.content_type or not file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="Le fichier doit être un fichier audio")
        
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Convertir en WAV si nécessaire
            audio = AudioSegment.from_file(temp_file_path)
            audio = audio.set_channels(1).set_frame_rate(16000)
            
            # Sauvegarder en WAV
            wav_path = temp_file_path.replace(".wav", "_converted.wav")
            audio.export(wav_path, format="wav")
            
            # Détecter la langue si non spécifiée
            if not language:
                try:
                    # Utiliser Whisper pour détecter la langue
                    result = model.transcribe(wav_path, language=None)
                    detected_lang = result["language"]
                    logger.info(f"Langue détectée : {detected_lang}")
                except Exception as e:
                    logger.warning(f"Erreur lors de la détection de langue : {e}")
                    detected_lang = "en"
            else:
                detected_lang = language
            
            # Transcrire avec la langue détectée
            logger.info(f"Transcription audio : langue={detected_lang}")
            
            result = model.transcribe(
                wav_path,
                language=detected_lang,
                task="transcribe"
            )
            
            transcribed_text = result["text"].strip()
            
            if not transcribed_text:
                raise HTTPException(status_code=400, detail="Aucun texte transcrit détecté")
            
            logger.info(f"Transcription réussie : '{transcribed_text[:50]}...'")
            
            return TranscriptionResponse(
                text=transcribed_text,
                language=detected_lang,
                confidence=result.get("confidence", None)
            )
            
        finally:
            # Nettoyer les fichiers temporaires
            try:
                os.unlink(temp_file_path)
                if os.path.exists(wav_path):
                    os.unlink(wav_path)
            except Exception as e:
                logger.warning(f"Erreur lors du nettoyage des fichiers temporaires : {e}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur lors de la transcription : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la transcription : {str(e)}")

@app.post("/transcribe-file/")
async def transcribe_file(request: TranscriptionRequest):
    try:
        if not request.audio_id:
            raise HTTPException(status_code=400, detail="audio_id requis")
        
        audio_path = os.path.join(OUTPUT_DIR, f"{request.audio_id}.wav")
        if not os.path.exists(audio_path):
            raise HTTPException(status_code=404, detail="Fichier audio non trouvé")
        
        # Détecter la langue si non spécifiée
        if not request.language:
            try:
                result = model.transcribe(audio_path, language=None)
                detected_lang = result["language"]
                logger.info(f"Langue détectée : {detected_lang}")
            except Exception as e:
                logger.warning(f"Erreur lors de la détection de langue : {e}")
                detected_lang = "en"
        else:
            detected_lang = request.language
        
        # Transcrire
        logger.info(f"Transcription fichier : {request.audio_id}, langue={detected_lang}")
        
        result = model.transcribe(
            audio_path,
            language=detected_lang,
            task="transcribe"
        )
        
        transcribed_text = result["text"].strip()
        
        if not transcribed_text:
            raise HTTPException(status_code=400, detail="Aucun texte transcrit détecté")
        
        logger.info(f"Transcription réussie : '{transcribed_text[:50]}...'")
        
        return {
            "text": transcribed_text,
            "language": detected_lang,
            "confidence": result.get("confidence", None)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur lors de la transcription : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la transcription : {str(e)}")

if __name__ == "__main__":
    import uvicorn # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=5002)