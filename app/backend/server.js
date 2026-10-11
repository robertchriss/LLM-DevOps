require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');

const app = express();
app.use(cors());
app.use(express.json());

const pool = new Pool({
  host: process.env.PGHOST || 'localhost',
  port: parseInt(process.env.PGPORT || '5432'),
  user: process.env.PGUSER || 'postgres',
  password: String(process.env.PGPASSWORD || 'postgres'),
  database: process.env.PGDATABASE || 'quizdb',
});

app.get('/healthz', (req, res) => {
  res.json({ status: 'ok' });
});

app.get('/api/lessons', async (req, res) => {
  try {
    const result = await pool.query('SELECT id, slug, title FROM lessons ORDER BY id ASC');
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
      'SELECT id, question, options, correct_index, explanation FROM quizzes WHERE lesson_id = $1',
      [lesson.id]
    );

    res.json({
      lesson,
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
      'SELECT id, question, correct_index, explanation FROM quizzes WHERE lesson_id = $1',
      [lesson_id]
    );

    const questions = quizResult.rows;
    let score = 0;
    const details = questions.map((q) => {
      const selectedIndex = parseInt(answers[q.id]);
      const isCorrect = selectedIndex === q.correct_index;
      if (isCorrect) score += 1;
      return {
        question_id: q.id,
        question: q.question,
        selected_index: selectedIndex,
        correct_index: q.correct_index,
        is_correct: isCorrect,
        explanation: q.explanation,
      };
    });

    const total = questions.length;
    await pool.query(
      'INSERT INTO user_scores (username, lesson_id, score, total) VALUES ($1, $2, $3, $4)',
      [username || 'Anonymous', lesson_id, score, total]
    );

    res.json({
      score,
      total,
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