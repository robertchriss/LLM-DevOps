import React, { useState, useEffect } from 'react';

const App = () => {
  const [lessons, setLessons] = useState([]);
  const [selectedLesson, setSelectedLesson] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/lessons');
        const data = await response.json();
        setLessons(data);
      } catch (error) {
        console.error('Error fetching data:', error);
        // Fallback sample data
        setLessons([
          { id: 1, title: 'Introduction to CKA', content: 'Sample content', quiz: ['Option 1', 'Option 2'] },
          { id: 2, title: 'Advanced CKA Topics', content: 'Sample content', quiz: ['Option A', 'Option B'] }
        ]);
      }
    };

    fetchData();
  }, []);

  const handleLessonClick = (lesson) => {
    setSelectedLesson(lesson);
  };

  return (
    <div className="App">
      <div className="sidebar">
        <h2>Lessons</h2>
        {lessons.map((lesson) => (
          <div key={lesson.id} onClick={() => handleLessonClick(lesson)} className="lesson-button">
            {lesson.title}
          </div>
        ))}
      </div>
      <div className="main-content">
        {selectedLesson ? (
          <div>
            <h2>{selectedLesson.title}</h2>
            <p>{selectedLesson.content}</p>
            <button className="quiz-button" onClick={() => console.log('Quiz taken')}>Take Quiz</button>
          </div>
        ) : (
          <div>
            <p>Select a lesson to begin</p>
            <button className="quiz-button" disabled>Take Quiz</button>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;