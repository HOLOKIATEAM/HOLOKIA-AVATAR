import axios from "axios";

const STT_SERVER_URL = import.meta.env.VITE_STT_URL || "/api/stt";

export const sttService = {
  generateText: async (audioFile, modelSize = "base") => {
    try {
      if (!(audioFile instanceof File)) {
        throw new Error("L'argument audioFile doit être un objet File");
      }

      console.log(`Génération STT: ${audioFile.name} (model: ${modelSize})`);

      const formData = new FormData();
      formData.append("file", audioFile);
      formData.append("model_size", modelSize);

      const response = await axios.post(STT_SERVER_URL, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      console.log("Réponse STT:", response.data);

      return {
        text: response.data.text,
        lang: response.data.lang,
        confidence: response.data.confidence,
      };
    } catch (err) {
      console.error("Erreur STT:", err);
      return {
        error: true,
        message: err.response?.data?.detail || "Échec lors de la transcription de l'audio",
      };
    }
  },
};