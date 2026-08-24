import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage';
import Loading from '../components/Loading';
import bookingService from '../services/bookingService';
import { formatCurrency, formatDateTime } from '../utils/format';

function BookingDetails() {
  const { bookingId } = useParams();
  const [booking, setBooking] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    bookingService
      .get(bookingId)
      .then(setBooking)
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load booking'));
  }, [bookingId]);

  if (!booking) {
    return error ? <ErrorMessage message={error} /> : <Loading label="Loading booking..." />;
  }

  return (
    <section className="detail-grid">
      <div className="card stack-md">
        <div className="inline-between">
          <h1>{booking.booking_reference}</h1>
          <span className={`status-pill ${booking.status.toLowerCase()}`}>{booking.status}</span>
        </div>
        <div className="info-list">
          <div><span>Event</span><strong>{booking.event.title}</strong></div>
          <div><span>Date & Time</span><strong>{formatDateTime(booking.event.event_date, booking.event.start_time, booking.event.end_time)}</strong></div>
          <div><span>Venue</span><strong>{booking.event.venue_name} • {booking.event.venue_location}</strong></div>
          <div><span>Seats</span><strong>{booking.seats.map((seat) => `${seat.row_label}${seat.seat_number}`).join(', ')}</strong></div>
          <div><span>Total</span><strong>{formatCurrency(booking.total_amount)}</strong></div>
        </div>
      </div>
      <aside className="card stack-md summary-card">
        <h2>QR Ticket</h2>
        {booking.qr_code_data_url ? (
          <img className="qr-image" src={booking.qr_code_data_url} alt={`QR code for ${booking.booking_reference}`} />
        ) : (
          <p className="muted">QR tickets are available for confirmed bookings.</p>
        )}
      </aside>
    </section>
  );
}

export default BookingDetails;

