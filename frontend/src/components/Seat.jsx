function Seat({ seat, isSelected, onClick }) {
  const stateClass = isSelected ? 'selected' : seat.status.toLowerCase();
  const disabled = seat.status !== 'AVAILABLE' && !isSelected;

  return (
    <button
      type="button"
      className={`seat-button ${stateClass}`}
      onClick={() => onClick(seat)}
      disabled={disabled}
      title={`${seat.row_label}${seat.seat_number} • ${seat.status}`}
    >
      {seat.row_label}{seat.seat_number}
    </button>
  );
}

export default Seat;

