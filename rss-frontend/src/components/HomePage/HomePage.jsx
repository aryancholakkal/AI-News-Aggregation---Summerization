import React, { useEffect, useState } from 'react';
import { fetchArticles } from '../../api';
import { FaThList, FaThLarge } from 'react-icons/fa';
import './HomePage.css';

const HomePage = () => {
  const [articles, setArticles] = useState([]);
  const [viewMode, setViewMode] = useState('grid'); 
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  useEffect(() => {
    fetchArticles(20)
      .then(res => {
        setArticles(res.data);
        console.log(res);
    })
      .catch(err => console.error('Failed to load articles', err));
  }, []);

  const toggleView = () => {
    setViewMode(prev => (prev === 'grid' ? 'list' : 'grid'));
  };

  const paginatedArticles = articles.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const totalPages = Math.ceil(articles.length / itemsPerPage);

  const handlePageChange = (page) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="container page-wrapper">

      <section className="toolbar">
        {/* <select className='form-select w-auto'>  
          <option>Newest First</option>
          <option>Oldest First</option>
        </select>*/}
        <button
            className="btn btn-outline-secondary d-flex align-items-center"
            onClick={toggleView}
            title="Toggle view"
            >
            {viewMode === 'list' ? <FaThLarge /> : <FaThList />}
        </button>
      </section>

      <div className={`row ${viewMode === 'grid' ? 'row-cols-1 row-cols-md-2 row-cols-lg-4' : 'row-cols-1'}`}>
        {paginatedArticles.map((article, idx) => (
          <div key={idx} className="col">
            <div className="card article-card">
              {/* <img
                src={article.image_url || 'https://via.placeholder.com/400x200'}
                className="card-img-top thumbnail"
                alt={article.title}
              /> */}
              <div className="card-body article-body">
                <h3 className="card-title">{article.title}</h3>
                <div className="meta">
                  {article.feed_name || 'Unknown'} •{' '}
                  {new Date(article.date || article.published_at).toLocaleDateString()}
                </div>
                <div className="summary">
                  {article.summary || 'No summary available.'}
                </div>
                <div className="actions">
                  <a href={article.url || article.link} target="_blank" rel="noreferrer">
                    Read More
                  </a>
                  <span className="did-you-know">Did you know?</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <nav className="pagination-controls">
          <ul className="pagination">
            {Array.from({ length: totalPages }).map((_, i) => (
              <li key={i} className={`page-item ${currentPage === i + 1 ? 'active' : ''}`}>
                <button className="page-link" onClick={() => handlePageChange(i + 1)}>
                  {i + 1}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </div>
  );
};

export default HomePage;
