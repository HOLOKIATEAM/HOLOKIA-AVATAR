from fastapi import FastAPI, HTTPException # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from fastapi.middleware.gzip import GZipMiddleware # type: ignore
from pydantic import BaseModel # type: ignore
from typing import List, Optional
from langchain_groq import ChatGroq # type: ignore
from langchain_core.output_parsers import StrOutputParser # type: ignore
from langchain_core.prompts import ChatPromptTemplate # type: ignore
from dotenv import load_dotenv # type: ignore
import logging
import os
from langdetect import detect # type: ignore
from datetime import datetime
import httpx # type: ignore
from cachetools import TTLCache # type: ignore
import time
import asyncio
import hashlib

# Chargement des variables d'environnement
load_dotenv()

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("avatar-backend")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY non définie dans les variables d'environnement")
    raise ValueError("GROQ_API_KEY est requise. Veuillez la définir dans le fichier .env")

# Initialisation du cache
cache = TTLCache(maxsize=500, ttl=86400)

# Initialisation du modèle LLM
try:
    llm = ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        max_tokens=200,
        temperature=0.5
    )
    logger.info("Modèle LLM Groq initialisé avec succès")
except Exception as e:
    logger.error(f"Erreur lors de l'initialisation du modèle LLM : {e}")
    raise

app = FastAPI(
    title="Avatar Backend API",
    description="API pour la génération de texte et la synthèse vocale",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

class Message(BaseModel):
    role: str
    content: str

class GenerateRequest(BaseModel):
    history: List[Message]

class GenerateResponse(BaseModel):
    text: str
    audioId: Optional[str] = None

class TTSRequest(BaseModel):
    text: str
    lang: str

@app.post("/api/generate", response_model=GenerateResponse)
async def generate_response(request: GenerateRequest):
    try:
        if not request.history:
            raise HTTPException(status_code=400, detail="L'historique de conversation ne peut pas être vide")
        
        recent_history = request.history[-5:]
        conversation = "\n".join(f"{msg.role}: {msg.content}" for msg in recent_history)
        
        user_message = next((msg.content for msg in reversed(recent_history) if msg.role == "user"), "")
        if not user_message.strip():
            raise HTTPException(status_code=400, detail="Aucun message utilisateur trouvé")
            
        try:
            detected_lang = detect(user_message)
            lang_mapping = {
                "en": "en",
                "fr": "fr",
                "ar": "ar",
                "ar-MA": "ar",
                "fr-FR": "fr",
                "en-US": "en",
                "en-GB": "en"
            }
            detected_lang = lang_mapping.get(detected_lang, "en")
            logger.info(f"Langue détectée : {detected_lang} pour le message : {user_message[:50]}...")
        except Exception as e:
            logger.warning(f"Erreur lors de la détection de langue : {e}, utilisation de l'anglais par défaut")
            detected_lang = "en"
            
        system_prompts = {
            "fr": "Tu es un avatar IA conversationnelle, tu t'appelles HOLOKIA. Réponds aux questions de l'utilisateur avec précision et sois bref.",
            "en": "You are a conversational AI avatar named HOLOKIA. Answer the user's questions accurately and be brief.",
            "ar": "أنت مساعد افتراضي ذكي اسمه HOLOKIA. أجب عن أسئلة المستخدم بدقة وباختصار.",
        }
        system_prompt = system_prompts.get(detected_lang, system_prompts["en"])
        
        cache_key = f"{conversation}_{detected_lang}"
        if cache_key in cache:
            logger.info(f"Utilisation du cache pour : {cache_key[:50]}...")
            response = cache[cache_key]
        else:
            try:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("user", conversation)
                ])
                parser = StrOutputParser()
                model = prompt | llm | parser
                
                start_time = time.time()
                response = model.invoke({"question": conversation})
                logger.info(f"Temps appel Groq : {time.time() - start_time} secondes")
                
                if not response or len(response.strip()) < 5:
                    logger.warning("Réponse LLM trop courte, utilisation du fallback")
                    response = system_prompts.get(detected_lang, system_prompts["en"])
                
                # Forcer le texte pré-généré pour les salutations
                if response.strip() == "Bonjour ! Comment puis-je vous aider aujourd'hui ?":
                    response = "Bonjour ! Je suis HOLOKIA, comment puis-je vous aider aujourd'hui ?"
                elif response.strip() in [
                    "Hello! I'm HOLOKIA. How can I assist you today?",
                    "Hello! I'm HOLOKIA, how can I assist you today?",
                ]:
                    response = "Hello! I am HOLOKIA, how can I assist you today?"
                elif response.strip() == "مرحبًا! كيف يمكنني مساعدتك اليوم؟":
                    response = "مرحبًا! أنا HOLOKIA، كيف يمكنني مساعدتك اليوم؟"

                cache[cache_key] = response
                logger.info(f"Réponse générée en {detected_lang} : {response}")
            except Exception as e:
                for attempt in range(3):
                    try:
                        start_time = time.time()
                        response = model.invoke({"question": conversation})
                        logger.info(f"Temps appel Groq (tentative {attempt + 1}) : {time.time() - start_time} secondes")
                        if not response or len(response.strip()) < 5:
                            logger.warning("Réponse LLM trop courte, utilisation du fallback")
                            response = system_prompts.get(detected_lang, system_prompts["en"])
                        
                        # Forcer le texte pré-généré pour les salutations
                        if response.strip() == "Bonjour ! Comment puis-je vous aider aujourd'hui ?":
                            response = "Bonjour ! Je suis HOLOKIA, comment puis-je vous aider aujourd'hui ?"
                        elif response.strip() in [
                            "Hello! I'm HOLOKIA. How can I assist you today?",
                            "Hello! I'm HOLOKIA, how can I assist you today?"
                        ]:
                            response = "Hello! I am HOLOKIA, how can I assist you today?"
                        
                        cache[cache_key] = response
                        return GenerateResponse(text=response)
                    except Exception as retry_e:
                        logger.warning(f"Échec appel LLM, tentative {attempt + 1}/3 : {retry_e}")
                        if attempt < 2:
                            await asyncio.sleep(2)
                        else:
                            logger.error(f"Erreur lors de l'appel au LLM après 3 tentatives : {retry_e}")
                            raise HTTPException(status_code=500, detail="Erreur lors de la génération de la réponse par le LLM")
        
        return GenerateResponse(text=response)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur inattendue dans generate_response : {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/api/tts")
async def generate_tts(request: TTSRequest):
    try:
        text = request.text
        lang = request.lang
        if not text.strip():
            raise HTTPException(status_code=400, detail="Le texte ne peut pas être vide")
        if not lang.strip():
            raise HTTPException(status_code=400, detail="La langue ne peut pas être vide")
        
        cache_key = hashlib.md5(f"{text}_{lang}".encode()).hexdigest()
        logger.info(f"Proxy TTS : génération audio pour '{text[:50]}...' (lang: {lang}, id: {cache_key})")
        
        async with httpx.AsyncClient(timeout=180.0) as client:  # Augmenté à 120s
            for attempt in range(3):
                try:
                    start_time = time.time()
                    response = await client.post(
                        "http://localhost:5000/generate-tts/",
                        json={"text": text, "lang": lang, "audio_id": cache_key}
                    )
                    logger.info(f"Temps requête TTS (tentative {attempt + 1}) : {time.time() - start_time} secondes")
                    #logger.info(response)
                    response.raise_for_status()
                    result = response.json()
                    #logger.info(result)
                    
                    """ if not result.get("audioId"):
                        raise HTTPException(status_code=500, detail="Le service TTS n'a pas retourné d'audioId") """
                        
                    logger.info(f"Audio généré avec succès : {result['audioPath']}")
                    return {
                        "audioPath": result["audioPath"],
                    }
                except httpx.TimeoutException as e:
                    logger.error(f"Timeout TTS, tentative {attempt + 1}/3 : {str(e)}")
                    if attempt < 2:
                        await asyncio.sleep(2)
                    else:
                        logger.error("Timeout lors de la requête TTS après 3 tentatives")
                        raise HTTPException(status_code=504, detail="Timeout lors de la génération TTS")
                except httpx.RequestError as e:
                    logger.error(f"Erreur requête TTS, tentative {attempt + 1}/3 : {str(e)}")
                    if attempt < 2:
                        await asyncio.sleep(2)
                    else:
                        logger.error(f"Erreur de requête TTS après 3 tentatives : {e}")
                        raise HTTPException(status_code=502, detail="Erreur de communication avec le service TTS")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur inattendue dans le proxy TTS : {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.get("/health")
async def health_check():
    try:
        if not GROQ_API_KEY:
            return {"status": "error", "message": "GROQ_API_KEY non configurée"}
            
        try:
            test_prompt = ChatPromptTemplate.from_messages([
                ("system", "Tu es un assistant test."),
                ("user", "Réponds 'OK'")
            ])
            parser = StrOutputParser()
            model = test_prompt | llm | parser
            response = model.invoke({"question": "test"})
            
            return {
                "status": "healthy",
                "service": "Avatar Backend API",
                "version": "1.0.0",
                "llm": "Groq - Llama-4-Scout",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        except Exception as e:
            return {"status": "error", "message": f"Erreur LLM : {str(e)}"}
            
    except Exception as e:
        return {"status": "error", "message": f"Erreur interne : {str(e)}"}

if __name__ == "__main__":
    import uvicorn # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=5001)