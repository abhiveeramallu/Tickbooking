import api from './api';

const waitlistService = {
  async join(eventId, category) {
    const { data } = await api.post(`/events/${eventId}/waitlist`, { category });
    return data;
  },

  async list() {
    const { data } = await api.get('/waitlist');
    return data;
  },

  async accept(offerId) {
    const { data } = await api.post(`/waitlist/offers/${offerId}/accept`);
    return data;
  }
};

export default waitlistService;

