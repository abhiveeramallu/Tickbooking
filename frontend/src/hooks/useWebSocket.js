import { useEffect, useRef } from 'react';

export default function useWebSocket(eventId, onMessage) {
  const messageRef = useRef(onMessage);

  useEffect(() => {
    messageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    if (!eventId) {
      return undefined;
    }

    const baseUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
    const socket = new WebSocket(`${baseUrl}/events/${eventId}`);
    const heartbeat = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send('ping');
      }
    }, 25000);

    socket.onmessage = (event) => {
      try {
        messageRef.current?.(JSON.parse(event.data));
      } catch {
      }
    };

    return () => {
      clearInterval(heartbeat);
      socket.close();
    };
  }, [eventId]);
}
