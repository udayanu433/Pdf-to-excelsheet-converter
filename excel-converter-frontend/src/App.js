// src/App.js
import React from 'react';
import ExcelGenerator from './ExcelGenerator'; 
// Keep the standard CSS import

function App() {
  // You may need to remove some of the default content in App.css 
  // or App.js's JSX to see only your converter.
  return (
    <div className="App">
      <ExcelGenerator />
    </div>
  );
}

export default App;