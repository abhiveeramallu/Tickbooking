import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage';
import bookingService from '../services/bookingService';
import { formatCurrency, formatDateTime, formatSeatLabel, getTimeRemaining } from '../utils/format';

function Checkout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [pendingHold, setPendingHold] = useState(() => {
    const stored = sessionStorage.getItem('ticket_hold');
    return location.state || (stored ? JSON.parse(stored) : null);
  });
  const [countdown, setCountdown] = useState(pendingHold ? getTimeRemaining(pendingHold.hold_expires_at) : '00:00');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!pendingHold) {
      return undefined;
    }
    const interval = setInterval(() => {
      const remaining = getTimeRemaining(pendingHold.hold_expires_at);
      setCountdown(remaining);
      if (remaining === '00:00') {
        sessionStorage.removeItem('ticket_hold');
        setPendingHold(null);
        setError('Your seat hold expired. Please select seats again.');
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [pendingHold]);

  const total = useMemo(
    () => pendingHold?.seats?.reduce((sum, seat) => sum + Number(seat.price), 0) || 0,
    [pendingHold]
  );

  const handleConfirmBooking = async () => {
    if (!pendingHold) {
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const booking = await bookingService.create({
        hold_id: pendingHold.hold_id,
        event_id: pendingHold.event_id
      });
      sessionStorage.removeItem('ticket_hold');
      navigate(`/bookings/${booking.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Booking could not be completed');
    } finally {
      setSubmitting(false);
    }
  };

  if (!pendingHold) {
    return (
      <div className="state-card">
        <p>No active hold found.</p>
      </div>
    );
  }

  return (
    <section className="detail-grid">
      <div className="card stack-md">
        <h1>Checkout</h1>
        <p className="muted">Payment processing is mocked for demonstration purposes.</p>
        <ErrorMessage message={error} />
        <div className="info-list">
          <div><span>Event</span><strong>{pendingHold.event.title}</strong></div>
          <div><span>Date & Time</span><strong>{formatDateTime(pendingHold.event.event_date, pendingHold.event.start_time, pendingHold.event.end_time)}</strong></div>
          <div><span>Venue</span><strong>{pendingHold.event.venue.name}</strong></div>
          <div><span>Seats</span><strong>{pendingHold.seats.map(formatSeatLabel).join(', ')}</strong></div>
        </div>
      </div>

      <aside className="card stack-md summary-card">
        <div className="hold-timer">Seats reserved for {countdown}</div>
        <div className="summary-line">
          <span>Total</span>
          <strong>{formatCurrency(total)}</strong>
        </div>
        <button type="button" className="button primary" onClick={handleConfirmBooking} disabled={submitting}>
          {submitting ? 'Confirming...' : 'Confirm Booking'}
        </button>
      </aside>
    </section>
  );
}

export default Checkout;

