import axios from 'axios';

const API = axios.create({
    baseURL:'http://localhost:8000/api',
});


export const fetchArticles = (limit = 20) => API.get(`/articles?limit=${limit}`);
export const fetchSummary = (id) => API.get(`/article/${id}/summary`);
export const fetchFeeds = () => API.get('/feeds');
export const addFeed = (feed) => API.post('/feeds', feed);
export const deleteFeed = (id) => API.delete(`/feeds/${id}`);