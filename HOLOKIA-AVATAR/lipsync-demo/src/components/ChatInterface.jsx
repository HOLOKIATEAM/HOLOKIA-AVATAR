import { lipsyncManager } from "../App";
import React, { useState, useContext, useEffect, useRef } from "react";
import { FaPlay, FaPause, FaPaperPlane, FaSpinner, FaMoon, FaSun, FaMinus, FaPlus, FaInfoCircle, FaTrash, FaGlobe } from "react-icons/fa";
import { apiClient } from "../config/api-config";
import { ttsService } from "../config/tts-service";
import "./ChatInterface.css";
import { Message } from "./Message.jsx";
import { Notification } from "./Notification.jsx";
import { AudioRecorder } from "./AudioRecorder.jsx";
import { LanguageIndicator } from "./LanguageIndicator.jsx";
import { franc } from "franc-min";

const LANGUAGES = [
  { value: "en", label: "English", gtts: "en" },
  { value: "fr", label: "Français", gtts: "fr" },
  { value: "ar", label: "العربية", gtts: "ar" },
];

const getLangLabel = (lang) => LANGUAGES.find(l => l.value === lang)?.label || lang;

// Fonction de détection de langue avec franc-min
const detectLanguage = (text) => {
  if (!text || text.trim().length < 3) return "en"; // Fallback pour les textes trop courts
  
  try {
    const detected = franc(text.trim());
    
    // Mapping des codes franc-min vers nos codes
    const langMapping = {
      "eng": "en",
      "fra": "fr", 
      "franc ":"fr",
      "ara": "ar",
      "arb": "ar", // Arabe standard
      "arz": "ar", // Arabe égyptien
      "acm": "ar", // Arabe irakien
      "afb": "ar", // Arabe du Golfe
      "ajp": "ar", // Arabe palestinien
      "apc": "ar", // Arabe levantin
      "apd": "ar", // Arabe soudanais
      "ary": "ar", // Arabe marocain
      "arz": "ar", // Arabe égyptien
      "auz": "ar", // Arabe ouzbek
      "avl": "ar", // Arabe bedawi
      "ayh": "ar", // Arabe hadrami
      "ayl": "ar", // Arabe libyen
      "ayn": "ar", // Arabe saoudien
      "ayp": "ar", // Arabe irakien
      "bbz": "ar", // Arabe babalia
      "pga": "ar", // Arabe soudanais
      "shu": "ar", // Arabe tchadien
      "ssh": "ar", // Arabe shihhi
    };
    
    const mappedLang = langMapping[detected] || detected;
    
    // Vérifier si la langue détectée est supportée
    if (LANGUAGES.some(l => l.value === mappedLang)) {
      return mappedLang;
    }
    
    // Fallback vers l'anglais si la langue n'est pas supportée
    return "en";
  } catch (error) {
    console.warn("Erreur lors de la détection de langue:", error);
    return "en";
  }
};

export const ChatInterface = () => {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState(() => JSON.parse(localStorage.getItem("chatMessages")) || []);
  const [isLoading, setIsLoading] = useState(false);
  const [audios, setAudios] = useState([]);
  const [theme, setTheme] = useState("neon");
  const [isMinimized, setIsMinimized] = useState(false);
  const [error, setError] = useState(null);
  const [notification, setNotification] = useState(null);
  const [langNotification, setLangNotification] = useState(null);
  const [sendFeedback, setSendFeedback] = useState(false);
  const [detectedLang, setDetectedLang] = useState("en"); // Langue détectée automatiquement
  const [showLangIndicator, setShowLangIndicator] = useState(false);
  const [isPlaying,setIsPlaying]=useState(false);
  const messagesEndRef = useRef(null);
  const audioRef = useRef(null);
  const [audioFile, setAudioFile] = useState("");

 
  
    useEffect(() => {
      const handleAudioEnded = () => {
        setAudioFile("");
        setIsPlaying(false);
      };
      audioRef.current?.addEventListener("ended", handleAudioEnded);
      return () => {
        audioRef.current?.removeEventListener("ended", handleAudioEnded);
      };
    }, []);
  
    useEffect(() => {
      if (!audioFile) {
        return;
      }
      //setDetectedVisemes([]);
  
      // Create or update audio element
      audioRef.current.src = audioFile; // Update source
      lipsyncManager.connectAudio(audioRef.current);
  
      // Connect audio to lipsync
      audioRef.current.play();
      setIsPlaying(true);
  
      // Cleanup
      return () => {
        if (audioRef.current) {
          audioRef.current.pause();
          // Do not clear src to allow reuse
        }
      };
    }, [audioFile]);
    const [detectedVisemes, setDetectedVisemes] = useState([]);
    const prevViseme = useRef(null);
  
    useEffect(() => {
      const analyzeAudio = () => {
        requestAnimationFrame(analyzeAudio);
        lipsyncManager.processAudio();
        const viseme = lipsyncManager.viseme;
        if (viseme !== prevViseme.current) {
          setDetectedVisemes((prev) => [...prev, viseme]);
          prevViseme.current = viseme;
        }
      };
      analyzeAudio();
    }, []);

  useEffect(() => {
    localStorage.setItem("chatMessages", JSON.stringify(messages));
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    document.body.className = `theme-${theme}`;
    return () => {
      document.body.className = "";
    };
  }, [theme]);

  // Détecter la langue quand le message change
  useEffect(() => {
    if (message.trim().length >= 3) {
      const lang = detectLanguage(message);
      if (lang !== detectedLang) {
        setDetectedLang(lang);
        setShowLangIndicator(true);
        setLangNotification(`Langue détectée : ${getLangLabel(lang)}`);
        
        // Masquer l'indicateur après 3 secondes
        setTimeout(() => {
          setShowLangIndicator(false);
        }, 3000);
      }
    }
  }, [message, detectedLang]);

  const getAnimationForResponse = (text) => {
    const lowerText = text.toLowerCase();
    if (lowerText.includes("bonjour") || lowerText.includes("salut") || lowerText.includes("hello")) {
      return "Greeting";
    }
    return "Idle";
  };

  const generateAudioAndLipsync = async (text, message, audios, detectedLang) => {
    setNotification("Génération audio et synchronisation labiale...");
    // Utiliser la langue détectée automatiquement par le backend
    const gttsLang = detectedLang || LANGUAGES.find(l => l.value === lang)?.gtts || "en";
    const newAudioId = `audio-${Date.now()}`;
    
    try {
      const result = await ttsService.generateAudio(text, newAudioId, gttsLang);
      
      if (result.error) {
        setError(result.message || "Erreur lors de la génération audio");
        setNotification(null);
        return null;
      }
      const path=`/audios/${result.audioId}.mp3`
      console.log(path)
      setAudioFile(path);
      return result.audioPath;
    } catch (error) {
      setError("Erreur lors de la génération audio");
      setNotification(null);
      return null;
    }
  };

const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    const userMessage = { text: message, sender: "user" };
    setMessages((prev) => [...prev, userMessage]);
    setMessage("");
    setSendFeedback(true);
    setTimeout(() => setSendFeedback(false), 300);
    setIsLoading(true);
    setNotification("Génération de la réponse...");
    try {
      const conversationHistory = messages.slice(-5).map((msg) => ({
        role: msg.sender === "user" ? "user" : "assistant",
        content: msg.text,
      }));
      conversationHistory.push({ role: "user", content: message });
      const response = await apiClient.generateResponse({ history: conversationHistory,detectedLanguage: detectedLang});
      console.log(response)
      // Le backend détecte automatiquement la langue, on l'utilise pour le TTS
      // On peut extraire la langue détectée du contexte ou utiliser la langue actuelle
      //const detectedLang = lang; // Pour l'instant, on utilise la langue sélectionnée
      
      // Toujours générer l'audio car le backend ne le fait pas automatiquement
      const audioPath = await generateAudioAndLipsync(response.text, message, audios, detectedLang);
      if (!audioPath) {
        setError("Erreur lors de la génération de l'audio");
        return;
      }
    
      const avatarMessage = { text: response.text, sender: "avatar" };
      setMessages((prev) => [...prev, avatarMessage]);
      setNotification(null);
    } catch (err) {
      setError(err.message || "Erreur lors de la génération de la réponse ou de l'audio.");
      setNotification(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetChat = () => {
    setMessages([]);
    localStorage.removeItem("chatMessages");
    setDetectedLang("en");
    setShowLangIndicator(false);
    setNotification("Conversation réinitialisée !");
    setTimeout(() => setNotification(null), 2000);
  };

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : prev === "light" ? "neon" : "dark"));
  };

  const toggleMinimize = () => setIsMinimized(!isMinimized);

    const toggleAudio = () => {
    if(isPlaying){
      audioRef.current.pause();
    }else{
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying)
  };

  // Notification auto-reset
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 3000);
      return () => clearTimeout(timer);
    }
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 3000);
      return () => clearTimeout(timer);
    }
    if (langNotification) {
      const timer = setTimeout(() => setLangNotification(null), 2000);
      return () => clearTimeout(timer);
    }
  }, [error, notification, langNotification]);

  // Nouvelle version : handleAudioTranscription accepte { text, lang }
  const handleAudioTranscription = (transcriptionResult) => {
    if (typeof transcriptionResult === "string") {
      setMessage(transcriptionResult);
      setTimeout(() => {
        const fakeEvent = { preventDefault: () => {} };
        handleSendMessage(fakeEvent);
      }, 100);
      return;
    }
    const { text, lang: detectedLang } = transcriptionResult || {};
    if (detectedLang) {
      // Mapping des langues détectées par Whisper vers nos codes
      const langMapping = {
        "en": "en",
        "fr": "fr", 
        "ar": "ar",
        "ar-MA": "ar"
      };
      const mappedLang = langMapping.get(detectedLang, detectedLang);
      setDetectedLang(mappedLang);
      setLangNotification(`Langue détectée : ${getLangLabel(mappedLang)}`);
    }
    setMessage(text || "");
    setTimeout(() => {
      const fakeEvent = { preventDefault: () => {} };
      handleSendMessage(fakeEvent);
    }, 100);
  };

  // Animation d'apparition pour les messages
  const [lastMsgIdx, setLastMsgIdx] = useState(-1);
  useEffect(() => {
    setLastMsgIdx(messages.length - 1);
  }, [messages]);

  // Envoi du message avec Ctrl+Enter
  const handleInputKeyDown = (e) => {
    if (e.key === "Enter") {
      handleSendMessage(e);
    }
  };

  return (
    <div className={`chat-container ${theme}`}>
      <audio ref={audioRef} controls className="w-full" />
      <div
        className={`fixed bottom-4 left-4 z-20 w-full max-w-[320px] rounded-lg shadow-xl p-4 transition-all duration-200 backdrop-blur-md ${
          theme === "dark"
            ? "bg-gray-800 bg-opacity-95 text-white"
            : theme === "light"
            ? "bg-white bg-opacity-95 text-gray-900"
            : "bg-gray-900 bg-opacity-95 text-white border border-blue-400"
        } ${isMinimized ? "h-12 overflow-hidden" : "min-h-[250px]"}`}
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold tracking-tight">Chat Avatar</h2>
          <div className="flex items-center gap-2">
            {/* Indicateur de langue détectée */}
            <LanguageIndicator 
              detectedLang={detectedLang}
              showIndicator={showLangIndicator}
              theme={theme}
            />
            <button
              onClick={toggleTheme}
              className="p-1.5 rounded-full hover:bg-gray-600 transition-all duration-200"
              title="Changer le thème"
              aria-label="Changer le thème"
            >
              {theme === "dark" ? (
                <FaSun className="w-4 h-4 text-yellow-400" />
              ) : theme === "light" ? (
                <FaMoon className="w-4 h-4 text-blue-600" />
              ) : (
                <FaSun className="w-4 h-4 text-blue-400" />
              )}
            </button>
            <button
              onClick={toggleMinimize}
              className="p-1.5 rounded-full hover:bg-gray-600 transition-all duration-200"
              title="Réduire/Agrandir"
              aria-label="Réduire ou agrandir le chat"
            >
              {isMinimized ? <FaPlus className="w-4 h-4" /> : <FaMinus className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {!isMinimized && (
          <>
            {error && <Notification message={error} type="error" onClose={() => setError(null)} />}
            {notification && <Notification message={notification} type="info" onClose={() => setNotification(null)} />}
            {langNotification && <Notification message={langNotification} type="info" onClose={() => setLangNotification(null)} />}

            <div className="messages flex flex-col gap-2 overflow-y-auto max-h-80 p-2" aria-live="polite">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`transition-all duration-300 ease-in-out ${idx === lastMsgIdx ? "animate-fade-in" : ""}`}
                  aria-label={msg.sender === "user" ? "Message utilisateur" : "Message avatar"}
                >
                  <Message text={msg.text} sender={msg.sender} />
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {isLoading && (
              <div className="flex justify-center items-center my-2">
                <FaSpinner className="animate-spin text-blue-500 text-2xl" aria-label="Chargement..." />
                <span className="ml-2 text-blue-500">L'avatar réfléchit...</span>
              </div>
            )}

            {/* Sélecteur d'audios supprimé - uniquement des audios générés dynamiquement */}

            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={toggleAudio}
                className={`p-2 rounded-full transition-all duration-200 ${
                  isPlaying ? "bg-red-500 hover:bg-red-600" : "bg-green-500 hover:bg-green-600"
                } shadow-sm`}
                title={isPlaying ? "Pause" : "Jouer"}
                aria-label={isPlaying ? "Pause l'audio" : "Jouer l'audio"}
              >
                {isPlaying ? <FaPause className="w-4 h-4" /> : <FaPlay className="w-4 h-4" />}
              </button>
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Votre message (détection automatique de langue)..."
                className={`flex-1 p-2 rounded-md border focus:outline-none focus:ring-2 focus:ring-blue-400 text-xs transition-all duration-200 ${
                  theme === "neon"
                    ? "bg-gray-800 text-blue-200 border-blue-400"
                    : theme === "dark"
                    ? "bg-gray-700 text-white border-gray-600"
                    : "bg-white text-gray-900 border-gray-300"
                }`}
                onKeyDown={handleInputKeyDown}
                aria-label="Saisir un message"
                title="Saisir un message (Ctrl+Entrée pour envoyer)"
              />
              <button
                onClick={handleSendMessage}
                className={`p-2 rounded-full transition-all duration-200 bg-blue-500 hover:bg-blue-600 text-white ${
                  sendFeedback ? "animate-pulse-icon" : ""
                } shadow-sm`}
                title="Envoyer"
                aria-label="Envoyer le message"
              >
                <FaPaperPlane className="w-4 h-4" />
              </button>
              <AudioRecorder onTranscription={handleAudioTranscription} lang={detectedLang} />
              <button
                onClick={handleResetChat}
                className="p-2 rounded-full bg-red-500 hover:bg-red-600 text-white transition-all duration-200 shadow-sm"
                title="Réinitialiser"
                aria-label="Réinitialiser la conversation"
              >
                <FaTrash className="w-4 h-4" />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};