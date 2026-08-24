import { Navigate, Route, Routes } from 'react-router-dom';

import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import AdminDashboard from './pages/AdminDashboard';
import BookingDetails from './pages/BookingDetails';
import Bookings from './pages/Bookings';
import Checkout from './pages/Checkout';
import CreateEvent from './pages/CreateEvent';
import CreateVenue from './pages/CreateVenue';
import EventDetails from './pages/EventDetails';
import Events from './pages/Events';
import Login from './pages/Login';
import OrganiserDashboard from './pages/OrganiserDashboard';
import Register from './pages/Register';
import SeatSelection from './pages/SeatSelection';
import Waitlist from './pages/Waitlist';

function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <main className="page-shell">
        <Routes>
          <Route path="/" element={<Events />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/events/:eventId" element={<EventDetails />} />
          <Route path="/events/:eventId/seats" element={<SeatSelection />} />
          <Route path="/checkout" element={<ProtectedRoute roles={['CUSTOMER']}><Checkout /></ProtectedRoute>} />
          <Route path="/bookings" element={<ProtectedRoute roles={['CUSTOMER']}><Bookings /></ProtectedRoute>} />
          <Route path="/bookings/:bookingId" element={<ProtectedRoute roles={['CUSTOMER']}><BookingDetails /></ProtectedRoute>} />
          <Route path="/waitlist" element={<ProtectedRoute roles={['CUSTOMER']}><Waitlist /></ProtectedRoute>} />
          <Route path="/waitlist/offer/:offerId" element={<ProtectedRoute roles={['CUSTOMER']}><Waitlist /></ProtectedRoute>} />
          <Route path="/organiser" element={<ProtectedRoute roles={['ORGANISER']}><OrganiserDashboard /></ProtectedRoute>} />
          <Route path="/organiser/events/new" element={<ProtectedRoute roles={['ORGANISER']}><CreateEvent /></ProtectedRoute>} />
          <Route path="/admin" element={<ProtectedRoute roles={['ADMIN']}><AdminDashboard /></ProtectedRoute>} />
          <Route path="/admin/venues/new" element={<ProtectedRoute roles={['ADMIN']}><CreateVenue /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;

