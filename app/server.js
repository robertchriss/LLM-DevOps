// Importing Express
const express = require('express');
// Create Express server instance
const app = express();

// Define GET /healthz endpoint to check server health
app.get('/healthz', (req, res) => {
  res.status(200).json({
    status: 'UP',
    message: 'The server is up and running.'
  });
});

// Define GET /api/lessons endpoint to return a list of lessons
app.get('/api/lessons', (req, res) => {
  const lessons = [
    { id: 1, title: 'Lesson 1: Introduction to TypeScript' },
    { id: 2, title: 'Lesson 2: Working with Classes and Interfaces' },
    { id: 3, title: 'Lesson 3: Advanced TypeScript Features' }
  ];
  res.status(200).json(lessons);
});

// Set the server to listen on port 3000
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});