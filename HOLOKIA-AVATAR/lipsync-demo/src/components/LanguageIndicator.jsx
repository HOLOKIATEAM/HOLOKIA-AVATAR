import React from "react";
import { FaGlobe } from "react-icons/fa";

const LanguageIndicator = ({ detectedLang, showIndicator, theme }) => {
  const getLangLabel = (lang) => {
    const languages = {
      "en": "English",
      "fr": "Français", 
      "ar": "العربية"
    };
    return languages[lang] || lang;
  };

  if (!showIndicator) return null;

  return (
    <div 
      className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs animate-pulse ${
        theme === "dark"
          ? "bg-blue-900 text-blue-200"
          : theme === "light"
          ? "bg-blue-100 text-blue-800"
          : "bg-blue-100 text-blue-800"
      }`}
      title={`Langue détectée : ${getLangLabel(detectedLang)}`}
    >
      <FaGlobe className="w-3 h-3" />
      <span>{getLangLabel(detectedLang)}</span>
    </div>
  );
};

export { LanguageIndicator };