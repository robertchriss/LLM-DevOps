require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());
app.use(cors());

const pool = new Pool({
  host: process.env.PGHOST,
  port: process.env.PGPORT,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  database: process.env.PGDATABASE,
  max: 20,
  min: 1
});

app.get('/healthz', (req, res) => {
  res.json({ status: 'ok' });
});

app.get('/api/lessons', async (req, res) => {
  try {
    const result = await pool.query('SELECT id, slug, title FROM lessons');
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch lessons' });
  }
});

app.get('/api/lessons/:slug', async (req, res) => {
  try {
    const { slug } = req.params;
    const lessonResult = await pool.query(
      'SELECT id, title, content FROM lessons WHERE slug = $1',
      [slug]
    );

    if (lessonResult.rowCount === 0) {
      return res.status(404).json({ error: 'Lesson not found' });
    }

    const lesson = lessonResult.rows[0];
    const quizResult = await pool.query(
      'SELECT id, question, correct_answer FROM quiz WHERE lesson_id = $1',
      [lesson.id]
    );

    res.json({
      lesson: lesson,
      quiz: quizResult.rows,
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch lesson and quiz' });
  }
});

app.post('/api/quiz/submit', async (req, res) => {
  try {
    const { username, lesson_id, answers } = req.body;
    const quizResult = await pool.query(
      'SELECT id, question, correct_answer FROM quiz WHERE lesson_id = $1',
      [lesson_id]
    );

    const questions = quizResult.rows;
    let score = 0;
    const details = questions.map((question) => {
      const userAnswer = answers[question.id];
      const correctAnswer = question.correct_answer;
      const isCorrect = userAnswer === correctAnswer;
      score += isCorrect ? 1 : 0;
      return { question: question.question, user_answer: userAnswer, correct_answer: correctAnswer, is_correct: isCorrect };
    });

    await pool.query(
      'INSERT INTO user_scores (username, lesson_id, score, details) VALUES ($1, $2, $3, $4)',
      [username, lesson_id, score, JSON.stringify(details)]
    );

    res.json({
      score,
      total: questions.length,
      details,
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to submit quiz' });
  }
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});