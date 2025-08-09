import React, { useRef, useState } from "react";
import PropTypes from "prop-types";
import { FaMicrophone, FaStop, FaSpinner } from "react-icons/fa";
import { sttService } from "../config/stt-config";

export const AudioRecorder = ({ onTranscription, lang = "en-us" }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new window.MediaRecorder(stream);
      audioChunksRef.current = [];
      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      mediaRecorderRef.current.onstop = handleStop;
      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      setError("Impossible d'accéder au micro : " + err.message);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleStop = async () => {
    setIsLoading(true);
    setError(null);
    const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("file", audioBlob, "audio.webm");
    formData.append("lang", lang);
    try {
      const response = await fetch(import.meta.env.VITE_STT_URL || "/api/stt", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error("Erreur serveur STT");
      const data = await response.json();
      if (data.text) {
        onTranscription(data.text);
      } else {
        setError("Aucune transcription reçue");
      }
    } catch (err) {
      setError("Erreur lors de la transcription : " + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={isRecording ? stopRecording : startRecording}
        className={`p-2 rounded-full transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400 ${
          isRecording ? "bg-red-500 text-white" : "bg-blue-500 text-white hover:bg-blue-600"
        }`}
        aria-label={isRecording ? "Arrêter l'enregistrement" : "Démarrer l'enregistrement vocal"}
        title={isRecording ? "Arrêter l'enregistrement" : "Démarrer l'enregistrement vocal"}
        disabled={isLoading}
      >
        {isRecording ? <FaStop /> : <FaMicrophone />}
      </button>
      {isLoading && <FaSpinner className="animate-spin text-blue-500" aria-label="Transcription en cours..." />}
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
};

AudioRecorder.propTypes = {
  onTranscription: PropTypes.func.isRequired,
  lang: PropTypes.string,
};