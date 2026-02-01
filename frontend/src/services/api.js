// src/services/api.js

// src/services/api.js in Frontend
import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';

export const processRepository = async (repoUrl) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/process`, { repo_url: repoUrl });
    return response.data;
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
};

export const searchCode = async (query, modelType) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/search`, { 
      params: { q: query, model: modelType } 
    });
    return response.data;
  } catch (error) {
    console.error("Search Error:", error);
    return [];
  }
};