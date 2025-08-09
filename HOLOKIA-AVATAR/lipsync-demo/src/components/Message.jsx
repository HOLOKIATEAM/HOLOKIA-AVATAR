import React from "react";
import PropTypes from "prop-types";

export const Message = ({ text, sender }) => (
  <div
    className={`message ${sender} px-3 py-2 my-1 rounded-lg shadow-md max-w-[85%] text-sm transition-all duration-200 ${
      sender === "user"
        ? "bg-blue-500 text-white self-end animate-slide-in-right"
        : "bg-gray-200 text-gray-900 self-start animate-slide-in-left"
    }`}
    aria-label={sender === "user" ? "Message utilisateur" : "Message avatar"}
    tabIndex={0}
  >
    <span>{text}</span>
  </div>
);

Message.propTypes = {
  text: PropTypes.string.isRequired,
  sender: PropTypes.oneOf(["user", "avatar"]).isRequired,
}; 