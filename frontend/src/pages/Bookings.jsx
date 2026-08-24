import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage';
import Loading from '../components/Loading';
import bookingService from '../services/bookingService';
import { formatDateTime } from '../utils/format';

function Bookings() {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadBookings = () => {
    setLoading(true);
    bookingService
      .list()
      .then(setBookings)
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load bookings'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadBookings();
  }, []);

  const handleCancel = async (bookingId) => {
    try {
      await bookingService.cancel(bookingId);
      loadBookings();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to cancel booking');
    }
  };

  if (loading) {
    return <Loading label="Loading bookings..." />;
  }

  return (
    <section className="stack-md">
      <div className="section-heading">
        <h1>Booking History</h1>
      </div>
      <ErrorMessage message={error} />
      <div className="card-grid">
        {bookings.map((booking) => (
          <article key={booking.id} className="card stack-sm">
            <div className="inline-between">
              <strong>{booking.booking_reference}</strong>
              <span className={`status-pill ${booking.status.toLowerCase()}`}>{booking.status}</span>
            </div>
            <div>{booking.event.title}</div>
            <div className="muted">{booking.seats.map((seat) => `${seat.row_label}${seat.seat_number}`).join(', ')}</div>
            <div className="muted">
              {formatDateTime(booking.event.event_date, booking.event.start_time, booking.event.end_time)}
            </div>
            <div className="inline-between">
              <Link className="button ghost" to={`/bookings/${booking.id}`}>View</Link>
              {booking.status === 'CONFIRMED' && (
                <button type="button" className="button ghost" onClick={() => handleCancel(booking.id)}>
                  Cancel
                </button>
              )}
            </div>
          </article>
        ))}
        {!bookings.length && <div className="state-card">No bookings yet.</div>}
      </div>
    </section>
  );
}

export default Bookings;

