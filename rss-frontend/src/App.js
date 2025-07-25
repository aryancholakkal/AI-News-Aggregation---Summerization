import React, {useState} from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import HomePage from './components/HomePage/HomePage';
import ManageFeedsPage from './components/ManageFeeds/ManageFeeds';


function App() {
  return (
    <Router>
      <header className="page-header">
        <h2>RSS Feed Summarizer</h2>
        <nav>
          <Link to="/">Home</Link>
          <Link to="/feeds">My Feeds</Link>
        </nav>
      </header>

      <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/feeds" element={<ManageFeedsPage />} />
      </Routes>
    </Router>
    
  );
}

export default App;