import os
import stat
from fastapi import FastAPI, HTTPException # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from fastapi.middleware.gzip import GZipMiddleware # type: ignore
from pydantic import BaseModel # type: ignore
import yaml
import io
import subprocess
import json
import logging
from pydub import AudioSegment # type: ignore
from gtts import gTTS # type: ignore
from fastapi.responses import FileResponse # type: ignore
from fastapi.concurrency import run_in_threadpool # type: ignore
from asyncio import Semaphore
import time
import hashlib
import platform

app = FastAPI(
    title="TTS Server",
    description="API de synthèse vocale et synchronisation labiale",
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

# Activer la compression GZip
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configurer les logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tts-server")

# Limiter à 5 requêtes simultanées
semaphore = Semaphore(5)

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

class SynthesisRequest(BaseModel):
    text: str
    lang: str
    audio_id: str | None = None
    speaker: str | None = None

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
        gtts_status = "unknown"
        try:
            test_tts = gTTS(text="test", lang="en", slow=False)
            gtts_status = "available"
        except Exception as e:
            gtts_status = f"error: {str(e)}"
        return {
            "status": "healthy",
            "service": "TTS Server",
            "version": "1.0.0",
            "languages": LANGUAGES,
            "rhubarb": "disponible",
            "output_dir": OUTPUT_DIR,
            "gtts_status": gtts_status,
            "timestamp": "2025-07-24T12:35:00Z"
        }
    except Exception as e:
        return {"status": "error", "message": f"Erreur interne : {str(e)}"}

@app.post("/generate-tts/")
async def generate_tts(request: SynthesisRequest):
    async with semaphore:
        return await run_in_threadpool(lambda: sync_generate_tts(request))

def sync_generate_tts(request: SynthesisRequest):
    try:
        if not request.text.strip():
            logger.error("Texte manquant dans la requête")
            raise HTTPException(status_code=400, detail="Le texte ne peut pas être vide")

        lang_map = {"fr": "fr", "en": "en", "ar": "ar", "fr-fr": "fr", "en-us": "en", "ar-MA": "ar"}
        normalized_lang = lang_map.get(request.lang, request.lang)
        if normalized_lang not in ["fr", "en", "ar"]:
            logger.error(f"Langue non supportée : {request.lang}")
            raise HTTPException(status_code=400, detail=f"Langue non supportée (attendu : fr, en, ar)")

        if request.speaker and request.speaker not in SPEAKERS:
            logger.error(f"Locuteur non supporté : {request.speaker}")
            raise HTTPException(status_code=400, detail=f"Locuteur non supporté (attendu : {SPEAKERS})")

        cache_key = hashlib.md5(f"{request.text}_{normalized_lang}".encode()).hexdigest()
        cache_audio_path = os.path.join(OUTPUT_DIR, f"{cache_key}.mp3")
    

        if os.path.exists(cache_audio_path):
            logger.info(f"Utilisation du cache pour : {cache_key}")
            return {
                "audioId": cache_key,
                "audioPath": f"/audios/{cache_key}.mp3",
            }

        audio_id = request.audio_id or cache_key
        audio_path = os.path.join(OUTPUT_DIR, f"{audio_id}.mp3")

        if os.path.exists(audio_path):
            logger.info(f"Utilisation du cache pour : {audio_id}")
            return {
                "audioId": audio_id,
                "audioPath": f"/audios/{audio_id}.mp3",
            }

        logger.info(f"Génération TTS : '{request.text[:50]}...' (lang: {normalized_lang}, id: {audio_id})")


        def generate_audio_with_retry(text, lang):
            for attempt in range(3):
                try:
                    start_time = time.time()
                    tts = gTTS(text=text, lang=lang, slow=False)
                    logger.info(f"Temps gTTS (tentative {attempt + 1}) : {time.time() - start_time} secondes")
                    return tts
                except Exception as e:
                    logger.warning(f"Échec gTTS, tentative {attempt + 1}/3 : {str(e)}")
                    if attempt < 2:
                        time.sleep(2)
                    else:
                        raise

        try:
            tts = generate_audio_with_retry(request.text, normalized_lang)
            start_time = time.time()
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            temp_audio_path = os.path.join(OUTPUT_DIR, f"{audio_id}.mp3")
            with open(temp_audio_path, "wb") as f:
                f.write(audio_buffer.getvalue())
            logger.info(f"Temps creation audio : {time.time() - start_time} secondes")
            logger.info(f"Audio MP3 temporaire généré : {temp_audio_path}")
            return {
                "audioId": audio_id,
                "audioPath": temp_audio_path,
            }

        except Exception as e:
            logger.error(f"Erreur lors de la génération audio : {e}")
            raise HTTPException(status_code=500, detail=f"Erreur lors de la génération audio : {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur inattendue dans generate_tts : {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur TTS")
            
if __name__ == "__main__":
    import uvicorn # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=5000)