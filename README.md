
# 🧠 Avatar RAG Project

Ce projet est une application web interactive combinant :

- 🎭 **Avatar 3D animé** avec synchronisation labiale et expressions faciales (React Three Fiber)
- 🧠 **Génération de texte par IA** via [Groq API]
- 🗣️ **Synthèse vocale (TTS)** + synchronisation labiale (Wawa-lipsync)
- 🎤 **Reconnaissance vocale (STT)**

---



## 📁 Structure du projet

```
HOLOKIA-AVATAR/
├── Back-end/
    ├──app              # API FastAPI + TTS + STT
│   │   ├── main.py             # Route principale pour la génération IA
│   │   ├── tts_server.py        # Service de synthèse vocale
│   │   ├── stt_server.py        # Service de reconnaissance vocale
│   │   ├── lipsync_config.yaml  # Configuration pour les serveurs
│   │   ├── .env                 # Clé API Groq (à ajouter)
│   ├── start_service.py        # Script pour lancer toutes les services du Backend
│   ├── requirements.txt    # Dépendances Python
│  
│
├── lipsync-demo/              # Application React (Vite + Three.js) basée sur Wawa-lipsync
│   ├── public/
│   │   ├── audios/      # Fichiers .mp3 des audios générés
│   │   ├── models       # l'avatar et ses animations
│   ├── src/                # Code source React
└── README.md
```

---

## ✅ Pré-requis
- [x] Une clé API Groq (à coller dans `.env`) dans Back-end
- [x] Git installé

---

## 🔧 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/HOLOKIATEAM/HOLOKIA-AVATAR.git
cd HOLOKIA-AVATAR
```

### 2. Ajouter le fichier `.env` dans le dossier `Back-end/app`

Exemple :

```ini
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Lancer tous les services
#### Back-end
Créer un environnement virtuel et installer les bibliothèques
```bash
    cd Back-end
    python -m venv avatar
    avatar\Scripts\activate
    pip install -r requirements.txt
```
##### Pour lancer tous les services avec le script
```bash
  python start_service.py
```
##### Ou lancer individuellemnt
TTS-SERVER
```bash
python -m uvicorn tts_server:app --host 0.0.0.0 --port 5000
```
STT-SERVER
```bash
python -m uvicorn stt_server:app --host 0.0.0.0 --port 5002
```
MAIN
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 5001
```
#### Front-end
```bash
  cd lipsync-demo
  npm install
  npm install franc-min
  npm run dev 
```
Cela démarre :

- 🧠 Backend IA (http://localhost:5001/docs)
- 🔊 TTS + lip-sync (http://localhost:5000/)
- 🎤 STT (http://localhost:5002/)
- 🌐 Frontend (http://localhost:5173/)

---

## 🧪 Test du projet

1. Accède à [http://localhost:5173/](http://localhost:5173/)
2. Écris un message dans le chat
3. L’IA génère une réponse avec :
   - Audio joué automatiquement
   - Bouche de l’avatar animée selon le texte
   - Expression faciale adaptée (joie, surprise…)
