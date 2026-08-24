import api from './api';

const eventService = {
  async list(params) {
    const { data } = await api.get('/events', { params });
    return data;
  },

  async get(eventId) {
    const { data } = await api.get(`/events/${eventId}`);
    return data;
  },

  async getSeats(eventId) {
    const { data } = await api.get(`/events/${eventId}/seats`);
    return data;
  },

  async holdSeats(eventId, seatIds) {
    const { data } = await api.post(`/events/${eventId}/holds`, { seat_ids: seatIds });
    return data;
  },

  async createEvent(payload) {
    const { data } = await api.post('/events', payload);
    return data;
  },

  async getVenues() {
    const { data } = await api.get('/venues');
    return data;
  },

  async getOrganiserDashboard() {
    const { data } = await api.get('/organiser/dashboard');
    return data;
  }
};

export default eventService;

