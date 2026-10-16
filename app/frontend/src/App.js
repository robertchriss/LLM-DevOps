import React, { useState, useEffect } from 'react';

const App = () => {
  const [lessons, setLessons] = useState([]);
  const [selectedLesson, setSelectedLesson] = useState(null);
  const [showQuiz, setShowQuiz] = useState(false);
  const [score, setScore] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchLessons = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/lessons');
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const data = await response.json();
        setLessons(data);
      } catch (err) {
        console.error('Error fetching lessons:', err);
        setError('Failed to fetch lessons. Showing sample data.');
        setLessons([
          {
            title: 'Sample Lesson',
            content: 'This is a sample content',
            quiz: [
              {
                question: 'Sample Question?',
                options: ['Option 1', 'Option 2', 'Option 3'],
                answer: 'Option 1',
                explanation: 'Explanation for Option 1'
              }
            ]
          }
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchLessons();
  }, []);

  const openQuiz = (lesson) => {
    setSelectedLesson(lesson);
    setShowQuiz(true);
  };

  const closeQuiz = () => {
    setSelectedLesson(null);
    setShowQuiz(false);
    setScore(0);
  };

  const handleAnswer = (question, selectedOption) => {
    const isCorrect = question.answer === selectedOption;
    if (isCorrect) {
      setScore((prevScore) => prevScore + 1);
    }
    console.log(isCorrect ? 'Correct' : 'Incorrect', question.explanation);
  };

  return (
    <div className="flex">
      <div className="w-1/4 bg-gray-200 p-4">
        <h1 className="text-2xl font-bold">CKA Learning Platform</h1>
        {lessons.map((lesson, index) => (
          <div key={index} className="my-4">
            <button
              className="bg-blue-500 text-white p-2 rounded"
              onClick={() => openQuiz(lesson)}
            >
              {lesson.title}
            </button>
          </div>
        ))}
      </div>
      <div className="w-3/4 p-4">
        {loading ? (
          <div className="text-center">Loading...</div>
        ) : error ? (
          <div className="text-center">{error}</div>
        ) : selectedLesson && showQuiz ? (
          <div>
            <h2 className="text-2xl font-bold">{selectedLesson.title}</h2>
            {selectedLesson.quiz && selectedLesson.quiz.map((question, index) => (
              <div key={index} className="my-4">
                <h3 className="text-lg">{question.question}</h3>
                {question.options && question.options.map((option) => (
                  <button
                    key={option}
                    className="bg-gray-300 text-gray-800 p-2 my-1 rounded"
                    onClick={() => handleAnswer(question, option)}
                  >
                    {option}
                  </button>
                ))}
              </div>
            ))}
            <button
              className="bg-red-500 text-white p-2 rounded"
              onClick={closeQuiz}
            >
              Close Quiz
            </button>
            <p className="text-xl">Score: {score}</p>
          </div>
        ) : (
          lessons.map((lesson, index) => (
            <div key={index} className="my-4 bg-white p-4 rounded shadow-md">
              <h2 className="text-xl font-bold">{lesson.title}</h2>
              <p>{lesson.content}</p>
              <button
                className="bg-blue-500 text-white p-2 rounded mt-4"
                onClick={() => openQuiz(lesson)}
              >
                Take Quiz
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default App;