import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage';
import eventService from '../services/eventService';

function CreateEvent() {
  const navigate = useNavigate();
  const [venues, setVenues] = useState([]);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    venue_id: '',
    title: '',
    description: '',
    event_type: 'MOVIE',
    event_date: '',
    start_time: '',
    end_time: '',
    status: 'PUBLISHED',
    standard_price: '',
    premium_price: ''
  });

  useEffect(() => {
    eventService
      .getVenues()
      .then(setVenues)
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load venues'));
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      const created = await eventService.createEvent({
        ...form,
        venue_id: Number(form.venue_id)
      });
      navigate(`/events/${created.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to create event');
    }
  };

  return (
    <section className="form-page">
      <form className="card stack-md" onSubmit={handleSubmit}>
        <h1>Create Event</h1>
        <ErrorMessage message={error} />
        <label>
          Venue
          <select value={form.venue_id} onChange={(event) => setForm((current) => ({ ...current, venue_id: event.target.value }))} required>
            <option value="">Select a venue</option>
            {venues.map((venue) => (
              <option key={venue.id} value={venue.id}>
                {venue.name} • {venue.location}
              </option>
            ))}
          </select>
        </label>
        <label>
          Title
          <input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} required />
        </label>
        <label>
          Description
          <textarea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} rows="4" />
        </label>
        <div className="form-grid">
          <label>
            Type
            <select value={form.event_type} onChange={(event) => setForm((current) => ({ ...current, event_type: event.target.value }))}>
              <option value="MOVIE">Movie</option>
              <option value="CONCERT">Concert</option>
            </select>
          </label>
          <label>
            Date
            <input type="date" value={form.event_date} onChange={(event) => setForm((current) => ({ ...current, event_date: event.target.value }))} required />
          </label>
          <label>
            Start
            <input type="time" value={form.start_time} onChange={(event) => setForm((current) => ({ ...current, start_time: event.target.value }))} required />
          </label>
          <label>
            End
            <input type="time" value={form.end_time} onChange={(event) => setForm((current) => ({ ...current, end_time: event.target.value }))} required />
          </label>
          <label>
            Standard Price
            <input type="number" min="1" step="0.01" value={form.standard_price} onChange={(event) => setForm((current) => ({ ...current, standard_price: event.target.value }))} required />
          </label>
          <label>
            Premium Price
            <input type="number" min="1" step="0.01" value={form.premium_price} onChange={(event) => setForm((current) => ({ ...current, premium_price: event.target.value }))} required />
          </label>
        </div>
        <button type="submit" className="button primary">Create Event</button>
      </form>
    </section>
  );
}

export default CreateEvent;

