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

export const searchCode = async (query) => {
  // Same as before...
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve([
        {
          id: 1,
          filename: "packages/react-dom/client.js",
          score: 0.89,
          code: `export function createRoot(container, options) {\n  if (!isValidContainer(container)) {\n    throw new Error('createRoot(...): Target container is not a DOM element.');\n  }\n  // ...\n}`
        }
      ]);
    }, 1000);
  });
};