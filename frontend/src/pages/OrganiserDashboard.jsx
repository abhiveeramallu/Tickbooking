import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage';
import Loading from '../components/Loading';
import eventService from '../services/eventService';
import { formatCurrency } from '../utils/format';

function OrganiserDashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    eventService
      .getOrganiserDashboard()
      .then(setDashboard)
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load organiser metrics'));
  }, []);

  if (!dashboard) {
    return error ? <ErrorMessage message={error} /> : <Loading label="Loading dashboard..." />;
  }

  return (
    <section className="stack-md">
      <div className="inline-between">
        <div>
          <h1>Organiser Dashboard</h1>
          <p className="muted">Event totals, bookings, and revenue.</p>
        </div>
        <Link to="/organiser/events/new" className="button primary">Create Event</Link>
      </div>
      <ErrorMessage message={error} />
      <div className="metric-grid">
        <div className="card"><span>Total Events</span><strong>{dashboard.total_events}</strong></div>
        <div className="card"><span>Total Bookings</span><strong>{dashboard.total_bookings}</strong></div>
        <div className="card"><span>Revenue</span><strong>{formatCurrency(dashboard.revenue)}</strong></div>
      </div>
      <div className="card stack-sm">
        <h2>Events</h2>
        {dashboard.events.map((event) => (
          <div key={event.id} className="list-row">
            <span>{event.title}</span>
            <span>{event.event_date}</span>
            <span>{event.tickets_sold} sold</span>
            <strong>{formatCurrency(event.revenue)}</strong>
          </div>
        ))}
        {!dashboard.events.length && <p className="muted">No events created yet.</p>}
      </div>
    </section>
  );
}

export default OrganiserDashboard;

