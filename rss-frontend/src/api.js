import axios from 'axios';

const API = axios.create({
    baseURL:'https://4bb48a35-d1a4-43d2-88cf-59c464af94f1-dev.e1-eu-north-azure.choreoapis.dev/default/briefly-backend/v1.0',
});


export const fetchArticles = (limit = 20) => API.get(`/articles?limit=${limit}`);
export const fetchSummary = (id) => API.get(`/article/${id}/summary`);
export const fetchFeeds = () => API.get('/feeds');
export const addFeed = (feed) => API.post('/feeds', feed);
export const deleteFeed = (id) => API.delete(`/feeds/${id}`);
export const didYouKnowContent = (url) => API.post('/convert-url', {url})
