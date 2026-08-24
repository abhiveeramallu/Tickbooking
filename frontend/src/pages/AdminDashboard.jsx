import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage';
import Loading from '../components/Loading';
import api from '../services/api';

function AdminDashboard() {
  const [venues, setVenues] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const loadVenues = () => {
    setLoading(true);
    api
      .get('/venues')
      .then((response) => setVenues(response.data))
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load venues'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadVenues();
  }, []);

  const handleDelete = async (venueId) => {
    try {
      await api.delete(`/venues/${venueId}`);
      loadVenues();
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to delete venue');
    }
  };

  if (loading) {
    return <Loading label="Loading venues..." />;
  }

  return (
    <section className="stack-md">
      <div className="inline-between">
        <div>
          <h1>Admin Dashboard</h1>
          <p className="muted">Manage venues and seat layouts.</p>
        </div>
        <Link to="/admin/venues/new" className="button primary">Create Venue</Link>
      </div>
      <ErrorMessage message={error} />
      <div className="card-grid">
        {venues.map((venue) => (
          <article key={venue.id} className="card stack-sm">
            <strong>{venue.name}</strong>
            <span>{venue.location}</span>
            <span className="muted">{venue.seats.length} seats configured</span>
            <button type="button" className="button ghost" onClick={() => handleDelete(venue.id)}>
              Delete
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

export default AdminDashboard;

