import Seat from './Seat';

function SeatMap({ seats, selectedSeats, onSeatClick }) {
  const selectedIds = new Set(selectedSeats.map((seat) => seat.id));
  const rows = seats.reduce((map, seat) => {
    const key = seat.row_label;
    if (!map[key]) {
      map[key] = [];
    }
    map[key].push(seat);
    return map;
  }, {});

  const sortedRows = Object.entries(rows).sort((left, right) => {
    const leftSeat = left[1][0];
    const rightSeat = right[1][0];
    return leftSeat.y_position - rightSeat.y_position;
  });

  return (
    <div className="seat-map card">
      <div className="screen-banner">SCREEN / STAGE</div>
      <div className="seat-legend">
        <span><i className="legend available" /> Available</span>
        <span><i className="legend selected" /> Selected</span>
        <span><i className="legend held" /> Held</span>
        <span><i className="legend booked" /> Booked</span>
      </div>
      <div className="seat-grid">
        {sortedRows.map(([rowLabel, rowSeats]) => (
          <div key={rowLabel} className="seat-row">
            <span className="row-label">{rowLabel}</span>
            <div className="row-seats">
              {rowSeats
                .sort((left, right) => left.seat_number - right.seat_number)
                .map((seat) => (
                  <Seat
                    key={seat.id}
                    seat={seat}
                    isSelected={selectedIds.has(seat.id)}
                    onClick={onSeatClick}
                  />
                ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default SeatMap;

