import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './Home';
import SemesterSelect from './SemesterSelect';
import ExcelGenerator from './ExcelGenerator'; // Your original converter component

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/scheme/:year" element={<SemesterSelect />} />
        {/* This path directs to your converter, passing scheme and semester */}
        <Route path="/converter/:year/:semester" element={<ExcelGenerator />} />
      </Routes>
    </Router>
  );
}

export default App;