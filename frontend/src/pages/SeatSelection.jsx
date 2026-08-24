import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage';
import Loading from '../components/Loading';
import SeatMap from '../components/SeatMap';
import { useAuth } from '../context/AuthContext';
import useWebSocket from '../hooks/useWebSocket';
import eventService from '../services/eventService';
import { formatCurrency, formatSeatLabel } from '../utils/format';

function SeatSelection() {
  const { eventId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [seats, setSeats] = useState([]);
  const [selectedSeats, setSelectedSeats] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([eventService.get(eventId), eventService.getSeats(eventId)])
      .then(([eventData, seatMap]) => {
        if (active) {
          setEvent(eventData);
          setSeats(seatMap.seats);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.response?.data?.detail || 'Unable to load seats');
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
  }, [eventId]);

  useWebSocket(eventId, (payload) => {
    if (payload.type !== 'SEATS_STATUS_CHANGED') {
      return;
    }
    setSeats((currentSeats) =>
      currentSeats.map((seat) => {
        const next = payload.seats.find((item) => item.seat_id === seat.id);
        return next ? { ...seat, status: next.status, hold_expires_at: next.hold_expires_at } : seat;
      })
    );
    setSelectedSeats((currentSelected) =>
      currentSelected.filter((seat) => !payload.seats.some((item) => item.seat_id === seat.id && item.status !== 'AVAILABLE'))
    );
  });

  const toggleSeat = (seat) => {
    setSelectedSeats((current) => {
      const exists = current.some((item) => item.id === seat.id);
      if (exists) {
        return current.filter((item) => item.id !== seat.id);
      }
      return [...current, seat];
    });
  };

  const handleContinue = async () => {
    if (!user) {
      navigate('/login', { state: { from: { pathname: `/events/${eventId}/seats` } } });
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const hold = await eventService.holdSeats(eventId, selectedSeats.map((seat) => seat.id));
      const pendingHold = {
        ...hold,
        event,
        seats: selectedSeats
      };
      sessionStorage.setItem('ticket_hold', JSON.stringify(pendingHold));
      navigate('/checkout', { state: pendingHold });
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to hold the selected seats');
      const seatMap = await eventService.getSeats(eventId);
      setSeats(seatMap.seats);
    } finally {
      setSubmitting(false);
    }
  };

  const total = selectedSeats.reduce((sum, seat) => sum + Number(seat.price), 0);

  if (loading) {
    return <Loading label="Loading seat map..." />;
  }

  return (
    <section className="detail-grid">
      <div className="stack-md">
        <div className="card">
          <h1>{event?.title}</h1>
          <p className="muted">Live seat status updates are synced for this event.</p>
        </div>
        <ErrorMessage message={error} />
        <SeatMap seats={seats} selectedSeats={selectedSeats} onSeatClick={toggleSeat} />
      </div>

      <aside className="card stack-md summary-card">
        <h2>Selected Seats</h2>
        <p>{selectedSeats.length ? selectedSeats.map(formatSeatLabel).join(', ') : 'No seats selected yet.'}</p>
        <div className="summary-line">
          <span>Total</span>
          <strong>{formatCurrency(total)}</strong>
        </div>
        <button
          type="button"
          className="button primary"
          onClick={handleContinue}
          disabled={!selectedSeats.length || submitting}
        >
          {submitting ? 'Reserving seats...' : 'Continue'}
        </button>
      </aside>
    </section>
  );
}

export default SeatSelection;
