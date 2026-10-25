// Realtime client - one WebSocket per signed-in tab, reconnects on its own (SPEC §5.5)
//
// Protocol: send {"type": "auth", "token"} first, then receive {"event", "data"} messages.
// The token travels in the first message, never in the URL, so it stays out of proxy logs.

import { refreshSession } from "./http";
import { useSession } from "./session";

export type RealtimeMessage = { event: string; data: Record<string, unknown> };
type Listener = (message: RealtimeMessage) => void;

const RETRY_STEPS_MS = [1_000, 2_000, 5_000, 10_000, 30_000];
const PING_EVERY_MS = 25_000;
const POLICY_VIOLATION = 1008;

function socketUrl(): string {
  // A static host (Vercel) cannot proxy WebSockets, so it may point straight at the API.
  const configured = import.meta.env.VITE_WS_URL as string | undefined;
  if (configured) return configured;
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}/ws`;
}

class RealtimeClient {
  private socket: WebSocket | null = null;
  private listeners = new Set<Listener>();
  private attempts = 0;
  private retryTimer: number | undefined;
  private pingTimer: number | undefined;
  private running = false;

  start(): void {
    if (this.running) return;
    this.running = true;
    this.open();
  }

  stop(): void {
    this.running = false;
    window.clearTimeout(this.retryTimer);
    window.clearInterval(this.pingTimer);
    this.socket?.close();
    this.socket = null;
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private open(): void {
    const token = useSession.getState().accessToken;
    if (!token) return;
    const socket = new WebSocket(socketUrl());
    this.socket = socket;

    socket.onopen = () => socket.send(JSON.stringify({ type: "auth", token }));
    socket.onmessage = (message) => {
      if (typeof message.data !== "string" || message.data === "pong") return;
      let parsed: RealtimeMessage;
      try {
        parsed = JSON.parse(message.data) as RealtimeMessage;
      } catch {
        return;
      }
      if (parsed.event === "ready") {
        this.attempts = 0;
        window.clearInterval(this.pingTimer);
        this.pingTimer = window.setInterval(() => socket.send("ping"), PING_EVERY_MS);
      }
      this.listeners.forEach((listener) => listener(parsed));
    };
    socket.onclose = (event) => {
      window.clearInterval(this.pingTimer);
      if (this.socket === socket) this.socket = null;
      if (!this.running) return;
      // An expired token closes the socket with 1008: refresh it before trying again.
      if (event.code === POLICY_VIOLATION) void refreshSession();
      const delay = RETRY_STEPS_MS[Math.min(this.attempts, RETRY_STEPS_MS.length - 1)];
      this.attempts += 1;
      this.retryTimer = window.setTimeout(() => this.open(), delay);
    };
  }
}

export const realtime = new RealtimeClient();
