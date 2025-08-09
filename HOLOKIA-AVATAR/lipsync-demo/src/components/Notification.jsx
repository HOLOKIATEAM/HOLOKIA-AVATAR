import React from "react";
import PropTypes from "prop-types";

export const Notification = ({ message, type = "info", onClose }) => (
  <div
    className={`notification fixed top-4 left-1/2 transform -translate-x-1/2 z-50 px-4 py-2 rounded shadow-lg text-center text-base font-medium transition-all duration-300 ${
      type === "error"
        ? "bg-red-500 text-white animate-shake"
        : type === "success"
        ? "bg-green-500 text-white"
        : "bg-blue-500 text-white"
    }`}
    role="alert"
    aria-live="assertive"
    tabIndex={0}
  >
    {message}
    {onClose && (
      <button
        className="ml-4 px-2 py-1 rounded bg-white text-blue-700 hover:bg-gray-200 transition"
        onClick={onClose}
        aria-label="Fermer la notification"
      >
        ×
      </button>
    )}
  </div>
);

Notification.propTypes = {
  message: PropTypes.string.isRequired,
  type: PropTypes.oneOf(["info", "success", "error"]),
  onClose: PropTypes.func,
}; 