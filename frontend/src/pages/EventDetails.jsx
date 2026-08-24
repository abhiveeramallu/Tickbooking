import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage';
import Loading from '../components/Loading';
import { useAuth } from '../context/AuthContext';
import eventService from '../services/eventService';
import waitlistService from '../services/waitlistService';
import { formatCurrency, formatDateTime } from '../utils/format';

function EventDetails() {
  const { eventId } = useParams();
  const { user } = useAuth();
  const [event, setEvent] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [category, setCategory] = useState('PREMIUM');

  useEffect(() => {
    eventService
      .get(eventId)
      .then(setEvent)
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load event'));
  }, [eventId]);

  const handleJoinWaitlist = async () => {
    setMessage('');
    setError('');
    try {
      await waitlistService.join(eventId, category);
      setMessage(`Joined the ${category} waitlist.`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to join waitlist');
    }
  };

  if (!event) {
    return error ? <ErrorMessage message={error} /> : <Loading label="Loading event..." />;
  }

  return (
    <section className="detail-grid">
      <div className="card stack-md">
        <div className="inline-between">
          <span className="pill">{event.event_type}</span>
          <span className="muted">{formatCurrency(Math.min(event.standard_price, event.premium_price))}</span>
        </div>
        <h1>{event.title}</h1>
        <p className="muted">{event.description}</p>
        <div className="info-list">
          <div><span>Date & Time</span><strong>{formatDateTime(event.event_date, event.start_time, event.end_time)}</strong></div>
          <div><span>Venue</span><strong>{event.venue.name}</strong></div>
          <div><span>Location</span><strong>{event.venue.location}</strong></div>
          <div><span>Standard</span><strong>{formatCurrency(event.standard_price)}</strong></div>
          <div><span>Premium</span><strong>{formatCurrency(event.premium_price)}</strong></div>
        </div>
        <Link to={`/events/${event.id}/seats`} className="button primary">
          Select Seats
        </Link>
      </div>

      <aside className="card stack-md">
        <h2>Waitlist</h2>
        <p className="muted">
          If seats are booked now, you can join the category waitlist and receive a time-limited offer.
        </p>
        <ErrorMessage message={error} />
        {message && <div className="success-banner">{message}</div>}
        {user?.role === 'CUSTOMER' ? (
          <>
            <label>
              Category
              <select value={category} onChange={(event) => setCategory(event.target.value)}>
                <option value="PREMIUM">Premium</option>
                <option value="STANDARD">Standard</option>
              </select>
            </label>
            <button type="button" className="button ghost" onClick={handleJoinWaitlist}>
              Join Waitlist
            </button>
          </>
        ) : (
          <p className="muted">Sign in as a customer to join the waitlist.</p>
        )}
      </aside>
    </section>
  );
}

export default EventDetails;

