import React, { useEffect, useState } from 'react';
import { fetchFeeds, addFeed, deleteFeed } from '../../api';
import './ManageFeeds.css';

const ManageFeedsPage = () => {
  const [feeds, setFeeds] = useState([]);
  const [url, setUrl] = useState('');
  const [name, setName] = useState('');
  const [status, setStatus] = useState('');
  const [variant, setVariant] = useState('info');

  useEffect(() => {
    loadFeeds();
  }, []);

  const loadFeeds = async () => {
    try {
      const res = await fetchFeeds();
      setFeeds(res.data);
    } catch (err) {
      setVariant('danger');
      setStatus('Failed to load feeds');
    }
  };

  const handleAddFeed = async (e) => {
    e.preventDefault();
    if (!url.trim()) {
      setVariant('warning');
      setStatus('Please enter a valid RSS URL');
      return;
    }
    try {
      const res = await addFeed({ url, name });
      setVariant('success');
      setStatus(res.data.message);
      setUrl('');
      setName('');
      loadFeeds();
    } catch (err) {
      setVariant('danger');
      setStatus(err.response?.data?.detail || 'Failed to add feed');
    }
  };

  const handleDeleteFeed = async (id) => {
    if (!window.confirm('Are you sure you want to delete this feed?')) return;
    try {
      const res = await deleteFeed(id);
      setVariant('success');
      setStatus(res.data.message);
      loadFeeds();
    } catch (err) {
      setVariant('danger');
      setStatus(err.response?.data?.detail || 'Failed to delete feed');
    }
  };

  return (
    <div className="container my-4">
      <h2 className="mb-4 border-bottom pb-2">Manage RSS Feeds</h2>

      {status && (
        <div className={`alert alert-${variant}`} role="alert">
          {status}
        </div>
      )}

      <form className="row g-2 mb-4" onSubmit={handleAddFeed}>
        <div className="col-md-5">
          <input
            type="url"
            className="form-control"
            placeholder="RSS Feed URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
        </div>
        <div className="col-md-4">
          <input
            type="text"
            className="form-control"
            placeholder="Feed Name (optional)"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="col-md-3">
          <button type="submit" className="btn btn-primary w-100">
            Add Feed
          </button>
        </div>
      </form>

      <div className="table-responsive">
        <table className="table table-bordered table-hover align-middle">
          <thead className="table-light">
            <tr>
              <th scope="col">#</th>
              <th scope="col">Name</th>
              <th scope="col">URL</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody>
            {feeds.length > 0 ? (
              feeds.map((feed, index) => (
                <tr key={feed.id}>
                  <th scope="row">{index + 1}</th>
                  <td>{feed.name}</td>
                  <td>
                    <a href={feed.url} target="_blank" rel="noopener noreferrer">
                      {feed.url}
                    </a>
                  </td>
                  <td>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleDeleteFeed(feed.id)}
                    >
                      🗑️ Remove
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="4" className="text-center">No feeds available</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ManageFeedsPage;
