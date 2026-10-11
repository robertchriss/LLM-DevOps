import React, { useState, useEffect } from 'react';
import axios from 'axios';

const App = () => {
  const [lessons, setLessons] = useState([]);
  const [activeTab, setActiveTab] = useState('lesson');
  const [quizData, setQuizData] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [score, setScore] = useState(0);
  const [showQuizResults, setShowQuizResults] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get('http://localhost:3000/api/lessons')
      .then((response) => {
        setLessons(response.data);
      })
      .catch((error) => {
        setError(error.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    axios.get('http://localhost:3000/api/quiz')
      .then((response) => {
        setQuizData(response.data);
      })
      .catch((error) => {
        setError(error.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const handleAnswerChange = (answerIndex) => {
    setSelectedAnswer(answerIndex);
  };

  const handleSubmitAnswer = () => {
    if (selectedAnswer === quizData[currentQuestion].correct) {
      setScore((prevScore) => prevScore + 1);
    }
    setSelectedAnswer(null);
    setCurrentQuestion((prevQuestion) => prevQuestion + 1);
  };

  const quizContent = (
    <div>
      {loading ? (
        <div>Loading...</div>
      ) : error ? (
        <div>Error: {error}</div>
      ) : (
        <>
          {currentQuestion < quizData.length ? (
            <div className="space-y-4">
              <h3 className="text-xl font-semibold">
                Q{currentQuestion + 1}: {quizData[currentQuestion].question}
              </h3>
              <div className="space-y-2">
                {quizData[currentQuestion].options.map((option, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <input
                      type="radio"
                      name="answer"
                      value={index}
                      checked={selectedAnswer === index}
                      onChange={() => handleAnswerChange(index)}
                    />
                    <label>{option}</label>
                  </div>
                ))}
              </div>
              <button
                onClick={handleSubmitAnswer}
                className="mt-4 bg-blue-500 hover:bg-blue-700 text-white px-4 py-2 rounded"
              >
                Submit
              </button>
            </div>
          ) : (
            <>
              <h3 className="text-xl font-semibold">Quiz Completed!</h3>
              <p className="text-gray-700">
                You scored {Math.round((score / quizData.length) * 100)}%.
              </p>
              <button
                onClick={() => setShowQuizResults(true)}
                className="mt-4 bg-green-500 hover:bg-green-700 text-white px-4 py-2 rounded"
              >
                View Results
              </button>
            </>
          )}
        </>
      )}
    </div>
  );

  const quizResultsModal = (
    <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white p-6 rounded shadow-lg">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-semibold">Quiz Results</h3>
          <span>{score}%</span>
        </div>
        {quizData.map((question, index) => (
          <div key={index} className="border-t pt-4">
            <div className="flex items-center space-x-2">
              <span className="text-sm">Q{index + 1}:</span>
              <span className="font-medium">{question.question}</span>
            </div>
            <div className="mt-2">
              <span className="text-sm">
                Correct Answer: {question.options[question.correct]}
              </span>
              <br />
              <span className="text-sm text-gray-600">{question.explanation}</span>
            </div>
          </div>
        ))}
        <button
          onClick={() => setShowQuizResults(false)}
          className="mt-4 bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded"
        >
          Close
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">
            Kubernetes Docs & Quiz Hub
          </h1>
          <div className="flex items-center space-x-4">
            <div className="relative">
              <span className="absolute right-0 top-0 bg-blue-500 text-white rounded-full px-2 py-1 text-xs">
                Score: {score}
              </span>
              <div className="flex items-center space-x-2">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 100 5.292M19 9.2l-7 7-7-7" />
                </svg>
                <span className="text-gray-700">User Stats</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8 grid grid-cols-12 gap-8">
        {/* Sidebar */}
        <aside className="col-span-3">
          <div className="space-y-2">
            <h2 className="text-lg font-semibold mb-4">Lessons</h2>
            {lessons.length === 0 && !error && (
              <div className="text-gray-500">No lessons available</div>
            )}
            {error && <div className="text-red-500">{error}</div>}
            {lessons.map((lesson, index) => (
              <div key={lesson.id} className="p-3 hover:bg-gray-50 rounded cursor-pointer">
                <h3 className="font-medium">{lesson.title}</h3>
                <p className="text-sm text-gray-600 mt-1">{lesson.description}</p>
              </div>
            ))}
          </div>
        </aside>

        {/* Main Content */}
        <main className="col-span-9">
          <div className="bg-white rounded-lg p-6 shadow-sm">
            <div className="flex space-x-4 mb-6">
              <button
                onClick={() => setActiveTab('lesson')}
                className={`px-4 py-2 rounded-t-lg ${activeTab === 'lesson' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600'}`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 inline-block mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 100 5.292M19 9.2l-7 7-7-7" />
                </svg>
                Lesson Content
              </button>
              <button
                onClick={() => setActiveTab('quiz')}
                className={`px-4 py-2 rounded-t-lg ${activeTab === 'quiz' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600'}`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 inline-block mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.345 0 2.772-1.756.426-3.78.552-5.751.321a1.724 1.724 0 00-1.065 2.572c-1.543-.94-2.924-2.985-2.37-4.961a1.724 1.724 0 00-2.572-1.065c-1.756-.426-1.756-2.345 0-2.772 1.756-.426 3.78-.552 5.751-.321z" />
                </svg>
                Quiz
              </button>
            </div>
            {activeTab === 'lesson' && (
              <div>
                <h3 className="text-xl font-semibold">Lesson Content</h3>
                <p className="text-gray-700">This is where the lesson content would be displayed.</p>
              </div>
            )}
            {activeTab === 'quiz' && quizContent}
          </div>
        </main>
      </div>
      {showQuizResults && quizResultsModal}
    </div>
  );
};

export default App;