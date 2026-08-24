import { useEffect, useState } from 'react';

import ErrorMessage from '../components/ErrorMessage';
import EventCard from '../components/EventCard';
import Loading from '../components/Loading';
import eventService from '../services/eventService';

function Events() {
  const [filters, setFilters] = useState({ search: '', event_type: '', date: '', location: '' });
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    eventService
      .list(filters)
      .then((result) => {
        if (active) {
          setEvents(result.items);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.response?.data?.detail || 'Unable to load events');
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [filters]);

  return (
    <section className="stack-lg">
      <div className="hero card">
        <div>
          <p className="eyebrow">Movies and concerts</p>
          <h1>Reserve seats with real-time availability</h1>
          <p className="muted">
            Holds expire automatically, bookings generate QR tickets, and waitlists are assigned FIFO.
          </p>
        </div>
        <div className="filter-grid">
          <input
            placeholder="Search title"
            value={filters.search}
            onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
          />
          <select
            value={filters.event_type}
            onChange={(event) => setFilters((current) => ({ ...current, event_type: event.target.value }))}
          >
            <option value="">All types</option>
            <option value="MOVIE">Movie</option>
            <option value="CONCERT">Concert</option>
          </select>
          <input
            type="date"
            value={filters.date}
            onChange={(event) => setFilters((current) => ({ ...current, date: event.target.value }))}
          />
          <input
            placeholder="Location"
            value={filters.location}
            onChange={(event) => setFilters((current) => ({ ...current, location: event.target.value }))}
          />
        </div>
      </div>

      <ErrorMessage message={error} />
      {loading ? (
        <Loading label="Loading events..." />
      ) : (
        <div className="card-grid">
          {events.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
          {!events.length && <div className="state-card">No events matched the current filters.</div>}
        </div>
      )}
    </section>
  );
}

export default Events;

