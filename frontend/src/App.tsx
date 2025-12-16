import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import NewReportPage from './pages/NewReportPage';
import ReportsPage from './pages/ReportsPage';
import TemplatesPage from './pages/TemplatesPage';
import EditorPage from './pages/EditorPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout><HomePage /></Layout>} />
        <Route path="/new-report" element={<Layout><NewReportPage /></Layout>} />
        <Route path="/reports" element={<Layout><ReportsPage /></Layout>} />
        <Route path="/templates" element={<Layout><TemplatesPage /></Layout>} />
        <Route path="/editor" element={<Layout><EditorPage /></Layout>} />
      </Routes>
    </Router>
  );
}

export default App;
