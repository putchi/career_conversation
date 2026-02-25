export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  message: string;
  history: Message[];
  session_id: string;
}

export interface ChatResponse {
  reply: string;
}

const sessionId = crypto.randomUUID();

export async function sendMessage(message: string, history: Message[]): Promise<string> {
  const body: ChatRequest = { message, history, session_id: sessionId };
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  }
  const data: ChatResponse = await res.json();
  return data.reply;
}
