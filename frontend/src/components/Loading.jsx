function Loading({ label = 'Loading...' }) {
  return (
    <div className="state-card">
      <div className="spinner" />
      <p>{label}</p>
    </div>
  );
}

export default Loading;

