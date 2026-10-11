import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link, Routes, Route, useNavigate } from 'react-router-dom';

const App = () => {
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLesson, setSelectedLesson] = useState(null);
  const [quizMode, setQuizMode] = useState(false);
  const [quizAnswers, setQuizAnswers] = useState({});
  const navigate = useNavigate();

  useEffect(() => {
    const fetchLessons = async () => {
      try {
        const response = await axios.get('http://localhost:5000/api/lessons');
        setLessons(response.data);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch lessons');
        setLoading(false);
      }
    };
    fetchLessons();
  }, []);

  const handleQuizSubmit = async () => {
    if (Object.keys(quizAnswers).length === 0) {
      alert('Please select an answer for each question');
      return;
    }
    
    try {
      await axios.post('http://localhost:5000/api/quiz/submit', {
        lessonId: selectedLesson._id,
        answers: quizAnswers
      });
      alert('Quiz submitted successfully!');
      setQuizMode(false);
    } catch (err) {
      alert('Failed to submit quiz');
    }
  };

  const handleAnswerChange = (questionId, answer) => {
    setQuizAnswers((prevAnswers) => ({
      ...prevAnswers,
      [questionId]: answer,
    }));
  };

  return (
    <div className="min-h-screen bg-gray-100 flex">
      {/* Left Sidebar */}
      <div className="w-64 bg-white h-screen p-4 border-r border-gray-200">
        <h2 className="text-xl font-bold mb-4">Lessons</h2>
        <div className="space-y-2">
          {lessons.map((lesson) => (
            <div
              key={lesson._id}
              className={`p-3 rounded-lg cursor-pointer transition-colors ${selectedLesson?._id === lesson._id ? 'bg-blue-50 border-blue-500' : 'hover:bg-gray-50'}`}
              onClick={() => {
                setSelectedLesson(lesson);
                setQuizMode(false);
              }}
            >
              <h3 className="font-semibold">{lesson.title}</h3>
              <p className="text-sm text-gray-500">{lesson.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-8">
        {loading && <div className="text-center py-12">Loading...</div>}
        {error && <div className="text-center py-12 text-red-500">{error}</div>}

        {selectedLesson ? (
          <div className="max-w-3xl mx-auto">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">{selectedLesson.title}</h2>
              <button
                onClick={() => setQuizMode(!quizMode)}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              >
                {quizMode ? 'View Lesson' : 'Take Quiz'}
              </button>
            </div>

            {quizMode ? (
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold mb-4">Quiz Time!</h3>
                <div className="space-y-4">
                  {selectedLesson.questions.map((question, index) => (
                    <div key={index} className="space-y-2">
                      <h4 className="font-medium">{question.text}</h4>
                      {question.options.map((option, optionIndex) => (
                        <label key={optionIndex} className="flex items-center space-x-2 cursor-pointer">
                          <input
                            type="radio"
                            name={`question-${index}`}
                            value={option.text}
                            checked={quizAnswers[question.id] === option.text}
                            onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                            className="form-radio h-4 w-4 text-blue-500"
                          />
                          <span className="text-gray-700">{option.text}</span>
                        </label>
                      ))}
                    </div>
                  ))}
                </div>
                <button
                  onClick={handleQuizSubmit}
                  className="mt-6 px-6 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
                >
                  Submit Quiz
                </button>
              </div>
            ) : (
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold mb-4">Lesson Content</h3>
                <div dangerouslySetInnerHTML={{ __html: selectedLesson.content }} />
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-12">Please select a lesson</div>
        )}
      </div>
    </div>
  );
};

export default App;