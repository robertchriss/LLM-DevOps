---
name: App Development & Package Standards
alwaysApply: true
---

# File Generation & Package Rules
- NEVER invent dummy version numbers in package.json (e.g., "^0.0.0"). 
- Always use standard pinned versions:
  - react: "^18.3.1"
  - react-dom: "^18.3.1"
  - react-scripts: "5.0.1"
  - tailwindcss: "^3.4.1"
  - express: "^4.19.2"
  - pg: "^8.11.5"
- Do NOT add conflicting devDependencies or outdated ESLint plugins.
- Output complete, fully functional code files without omitting placeholders or leaving `// TODO` comments.