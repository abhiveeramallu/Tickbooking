import { Link } from 'react-router-dom';

import { formatCurrency, formatDateTime } from '../utils/format';

function EventCard({ event }) {
  return (
    <article className="card event-card">
      <div className="event-card-top">
        <span className="pill">{event.event_type}</span>
        <span className="muted">{formatCurrency(event.starting_price)}</span>
      </div>
      <h3>{event.title}</h3>
      <p className="muted">{event.description || 'Book seats for this event.'}</p>
      <div className="stack-sm">
        <span>{formatDateTime(event.event_date, event.start_time, event.end_time)}</span>
        <span>{event.venue.name} • {event.venue.location}</span>
      </div>
      <Link to={`/events/${event.id}`} className="button primary">
        View Event
      </Link>
    </article>
  );
}

export default EventCard;

