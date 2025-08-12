import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { fetchArticles, didYouKnowContent } from '../../api';
import { FaThList, FaThLarge } from 'react-icons/fa';
import './HomePage.css';

const HomePage = () => {
  const [articles, setArticles] = useState([]);
  const [viewMode, setViewMode] = useState('grid'); 
  const [currentPage, setCurrentPage] = useState(1);
  const [dykContent, setDykContent] = useState(null);
  const [loadingId, setLoadingId] = useState(null);
  const [showModal, setShowModal] = useState(false);
  
  const [searchParams] = useSearchParams();
  const tagFilter = searchParams.get("tag"); // <-- Get tag from URL

  const itemsPerPage = 8;

  useEffect(() => {
    fetchArticles(40)
      .then(res => {
        let data = res.data;
        if (tagFilter) {
          data = data.filter(article => article.tag === tagFilter);
        }
        setArticles(data);
        console.log(data);
        setCurrentPage(1); // reset to page 1 when tag changes
      })
      .catch(err => console.error('Failed to load articles', err));
  }, [tagFilter]);

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
  
  const handleContent = async (url, id) => {
    setLoadingId(id);
    try {
      const { data } = await didYouKnowContent(url);
      setDykContent(data.did_you_know);
      setShowModal(true);
    } catch (err) {
      console.error('Error fetching Did You Know content:', err);
      setDykContent('Failed to fetch Did You Know content.');
      setShowModal(true);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="container page-wrapper">

      <section className="toolbar">
        <button
            className="btn btn-outline-secondary d-flex align-items-center"
            onClick={toggleView}
            title="Toggle view"
            >
            {viewMode === 'list' ? <FaThLarge /> : <FaThList />}
        </button>
      </section>

      <h3 className="mb-3">
        {tagFilter ? `Showing ${tagFilter} Articles` : 'All Articles'}
      </h3>

      <div className={`row ${viewMode === 'grid' ? 'row-cols-1 row-cols-md-2 row-cols-lg-4' : 'row-cols-1'}`}>
        {paginatedArticles.map((article, idx) => (
          <div key={idx} className="col">
            <div className="card article-card">
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
                  <button
                    className="did-you-know"
                    onClick={() => handleContent(article.url || article.link, idx)}
                    disabled={loadingId === idx} 
                  >
                    {loadingId === idx ? (
                      <span className="spinner-border spinner-border-sm text-primary" role="status" />
                    ) : (
                      'Did you know?'
                    )}
                  </button>                
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

      {showModal && (
        <div className="modal fade show" style={{ display: 'block', background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">💡 Did You Know?</h5>
                <button type="button" className="btn-close" onClick={() => setShowModal(false)}></button>
              </div>
              <div className="modal-body">
                <p>{dykContent}</p>
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Close</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HomePage;
