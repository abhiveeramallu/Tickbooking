import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import ErrorMessage from '../components/ErrorMessage';
import api from '../services/api';

function CreateVenue() {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [form, setForm] = useState({ name: '', location: '' });
  const [rows, setRows] = useState([
    { row_label: 'A', seats: 5, category: 'PREMIUM' },
    { row_label: 'B', seats: 5, category: 'STANDARD' }
  ]);

  const updateRow = (index, field, value) => {
    setRows((current) =>
      current.map((row, rowIndex) => (rowIndex === index ? { ...row, [field]: value } : row))
    );
  };

  const addRow = () => {
    setRows((current) => [...current, { row_label: '', seats: 5, category: 'STANDARD' }]);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const seats = rows.flatMap((row, rowIndex) =>
      Array.from({ length: Number(row.seats) }, (_, seatIndex) => ({
        row_label: row.row_label.toUpperCase(),
        seat_number: seatIndex + 1,
        category: row.category,
        x_position: seatIndex,
        y_position: rowIndex
      }))
    );

    try {
      await api.post('/venues', { ...form, seats });
      navigate('/admin');
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to create venue');
    }
  };

  return (
    <section className="form-page">
      <form className="card stack-md" onSubmit={handleSubmit}>
        <h1>Create Venue</h1>
        <ErrorMessage message={error} />
        <label>
          Venue Name
          <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required />
        </label>
        <label>
          Location
          <input value={form.location} onChange={(event) => setForm((current) => ({ ...current, location: event.target.value }))} required />
        </label>
        <div className="stack-sm">
          <div className="inline-between">
            <h2>Rows</h2>
            <button type="button" className="button ghost" onClick={addRow}>Add Row</button>
          </div>
          {rows.map((row, index) => (
            <div key={`${row.row_label}-${index}`} className="form-grid">
              <label>
                Row Label
                <input value={row.row_label} onChange={(event) => updateRow(index, 'row_label', event.target.value)} required />
              </label>
              <label>
                Seat Count
                <input type="number" min="1" value={row.seats} onChange={(event) => updateRow(index, 'seats', event.target.value)} required />
              </label>
              <label>
                Category
                <select value={row.category} onChange={(event) => updateRow(index, 'category', event.target.value)}>
                  <option value="PREMIUM">Premium</option>
                  <option value="STANDARD">Standard</option>
                </select>
              </label>
            </div>
          ))}
        </div>
        <button type="submit" className="button primary">Create Venue</button>
      </form>
    </section>
  );
}

export default CreateVenue;

