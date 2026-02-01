// src/services/api.js

export const processRepository = async (repoUrl) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        status: "indexed",
        // Mock GitHub Metadata
        details: {
          owner: "facebook",
          name: "react",
          description: "A declarative, efficient, and flexible JavaScript library for building user interfaces.",
          stars: 213000,
          forks: 45000,
          avatar: "https://avatars.githubusercontent.com/u/69631?v=4" // React logo
        },
        // Mock File Tree (Recursive structure)
        fileTree: [
          {
            name: "packages",
            type: "folder",
            children: [
              { name: "react", type: "folder", children: [{ name: "index.js", type: "file" }] },
              { name: "react-dom", type: "folder", children: [{ name: "client.js", type: "file" }] }
            ]
          },
          { name: "scripts", type: "folder", children: [{ name: "build.js", type: "file" }] },
          { name: "README.md", type: "file" },
          { name: "package.json", type: "file" }
        ]
      });
    }, 1500);
  });
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