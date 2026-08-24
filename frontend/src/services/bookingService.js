import api from './api';

const bookingService = {
  async create(payload) {
    const { data } = await api.post('/bookings', payload);
    return data;
  },

  async list() {
    const { data } = await api.get('/bookings');
    return data.items;
  },

  async get(bookingId) {
    const { data } = await api.get(`/bookings/${bookingId}`);
    return data;
  },

  async cancel(bookingId) {
    const { data } = await api.post(`/bookings/${bookingId}/cancel`);
    return data;
  }
};

export default bookingService;

