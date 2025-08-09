import axios from "axios";
// En production, utiliser des URLs relatives pour passer par le proxy Nginx
const TTS_SERVER_URL = import.meta.env.VITE_TTS_URL || "http://localhost:5000/generate-tts/";
const FRONT_URL = import.meta.env.MODE === "production"
  ? (import.meta.env.VITE_FRONT_URL || "")
  : (import.meta.env.VITE_FRONT_URL || "http://localhost:5173");


export const ttsService = {
  generateAudio: async (text, audioId, language = "en", speaker = "female-pt-4") => {
    try {
      console.log(`Génération TTS: ${text} (${language}) -> ${audioId}`);
      const response = await axios.post(
        TTS_SERVER_URL,
        { text, audio_id: audioId, lang: language, speaker },
        { headers: { "Content-Type": "application/json" } }
      );
      console.log("Réponse TTS:", response.data);
      return response.data
    } catch (error) {
      return {
        error: true,
        message: error.response?.data?.detail || error.message,
      };
    }
  },
};