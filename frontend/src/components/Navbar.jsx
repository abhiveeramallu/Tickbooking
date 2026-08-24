import { Link, NavLink } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="navbar">
      <Link to="/" className="brand">
        <span className="brand-mark">TKT</span>
        <span>Ticket Booking</span>
      </Link>
      <nav className="nav-links">
        <NavLink to="/">Events</NavLink>
        {user?.role === 'CUSTOMER' && <NavLink to="/bookings">Bookings</NavLink>}
        {user?.role === 'CUSTOMER' && <NavLink to="/waitlist">Waitlist</NavLink>}
        {user?.role === 'ORGANISER' && <NavLink to="/organiser">Organiser</NavLink>}
        {user?.role === 'ADMIN' && <NavLink to="/admin">Admin</NavLink>}
      </nav>
      <div className="nav-actions">
        {user ? (
          <>
            <div className="user-chip">
              <span>{user.name}</span>
              <small>{user.role}</small>
            </div>
            <button type="button" className="button ghost" onClick={logout}>
              Logout
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className="button ghost">Login</Link>
            <Link to="/register" className="button primary">Register</Link>
          </>
        )}
      </div>
    </header>
  );
}

export default Navbar;

