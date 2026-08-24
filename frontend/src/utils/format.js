export function formatDateTime(date, startTime, endTime) {
  const start = new Date(`${date}T${startTime}`);
  const end = endTime ? new Date(`${date}T${endTime}`) : null;
  const day = new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  }).format(start);
  const startLabel = new Intl.DateTimeFormat('en-IN', {
    hour: 'numeric',
    minute: '2-digit'
  }).format(start);
  const endLabel = end
    ? new Intl.DateTimeFormat('en-IN', { hour: 'numeric', minute: '2-digit' }).format(end)
    : null;
  return `${day} • ${startLabel}${endLabel ? ` - ${endLabel}` : ''}`;
}

export function formatCurrency(amount) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2
  }).format(Number(amount || 0));
}

export function formatSeatLabel(seat) {
  return `${seat.row_label}${seat.seat_number}`;
}

export function getTimeRemaining(timestamp) {
  const diff = new Date(timestamp).getTime() - Date.now();
  if (diff <= 0) {
    return '00:00';
  }
  const totalSeconds = Math.floor(diff / 1000);
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
  const seconds = String(totalSeconds % 60).padStart(2, '0');
  return `${minutes}:${seconds}`;
}

