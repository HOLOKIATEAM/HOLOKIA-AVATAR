import axios from "axios";

// En production, utiliser des URLs relatives pour passer par le proxy Nginx
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5001";

const apiClient = {
  generateResponse: async (payload) => {
    try {
      const response = await axios.post(`${BASE_URL}/api/generate`, payload);
      return response.data;
    } catch (error) {
      return {
        error: true,
        message: error.response?.data?.detail || error.message,
      };
    }
  },
};

export { apiClient };