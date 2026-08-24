import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage';
import Loading from '../components/Loading';
import waitlistService from '../services/waitlistService';

function Waitlist() {
  const { offerId } = useParams();
  const navigate = useNavigate();
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(!offerId);

  useEffect(() => {
    if (offerId) {
      return;
    }
    waitlistService
      .list()
      .then(setEntries)
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load waitlist entries'))
      .finally(() => setLoading(false));
  }, [offerId]);

  const handleAccept = async () => {
    try {
      const booking = await waitlistService.accept(offerId);
      navigate(`/bookings/${booking.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to accept offer');
    }
  };

  if (offerId) {
    return (
      <section className="card offer-card stack-md">
        <h1>Waitlist Offer</h1>
        <p className="muted">This seat is reserved for you until the offer expires.</p>
        <ErrorMessage message={error} />
        <button type="button" className="button primary" onClick={handleAccept}>
          Accept Offer
        </button>
      </section>
    );
  }

  if (loading) {
    return <Loading label="Loading waitlist..." />;
  }

  return (
    <section className="stack-md">
      <h1>Your Waitlist Entries</h1>
      <ErrorMessage message={error} />
      <div className="card-grid">
        {entries.map((entry) => (
          <article key={entry.id} className="card stack-sm">
            <strong>{entry.event_title}</strong>
            <span>{entry.category}</span>
            <span className={`status-pill ${entry.status.toLowerCase()}`}>{entry.status}</span>
            <span className="muted">Position #{entry.position}</span>
          </article>
        ))}
        {!entries.length && <div className="state-card">No waitlist entries yet.</div>}
      </div>
    </section>
  );
}

export default Waitlist;

