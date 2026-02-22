import { sendMessage, type Message } from './api.js';

// ── Runtime config (injected by backend at /config.js; fallback to build-time env for local dev) ──
const _cfg = (window as any).CAREER_CONFIG ?? {};
const OWNER_NAME   = _cfg.ownerName   || import.meta.env.VITE_OWNER_NAME   || '';
const OWNER_TITLE  = _cfg.ownerTitle  || import.meta.env.VITE_OWNER_TITLE  || '';
const LINKEDIN_URL = _cfg.linkedinUrl || import.meta.env.VITE_LINKEDIN_URL || '#';

// ── State ─────────────────────────────────────────────────────
let history: Message[] = [];
let isTyping = false;

const SUGGESTIONS = [
  "What's your technical background?",
  "Tell me about your management experience",
  "What industries have you worked in?",
  "Are you open to relocation?",
];

// ── DOM ───────────────────────────────────────────────────────
const app = document.getElementById('app')!;

app.innerHTML = `
  <!-- Grid background -->
  <div style="position:absolute;inset:0;z-index:0;
    background-image:
      linear-gradient(hsla(200,15%,18%,0.4) 1px, transparent 1px),
      linear-gradient(90deg, hsla(200,15%,18%,0.4) 1px, transparent 1px);
    background-size:40px 40px;pointer-events:none;"></div>

  <!-- Header -->
  <header class="header glass-surface">
    <div class="header-left">
      <div class="header-icon glow-primary">🤖</div>
      <div>
        <div class="header-title">
          ${OWNER_NAME}
          <span class="available-badge"><span class="available-dot"></span>Available for opportunities</span>
        </div>
        <div class="header-subtitle">${OWNER_TITLE}</div>
      </div>
    </div>
    <div class="header-right">
      <div class="status-pill">
        <span class="status-pill-dot"></span>Neural
      </div>
      <div class="status-pill">
        <span class="status-pill-dot" style="background:var(--accent)"></span>Active
      </div>
    </div>
  </header>

  <!-- Messages -->
  <div id="messages" class="messages"></div>

  <!-- Suggestions -->
  <div id="suggestions" class="suggestions">
    ${SUGGESTIONS.map(s => `<button class="suggestion-chip" data-prompt="${s}">${s}</button>`).join('')}
  </div>

  <!-- Input -->
  <div class="input-area">
    <textarea
      id="chat-input"
      class="chat-input"
      placeholder="Send a message to your digital twin..."
      rows="1"
    ></textarea>
    <button id="clear-btn" class="clear-btn" title="Clear conversation">↺</button>
    <button id="send-btn" class="send-btn" disabled title="Send">➤</button>
  </div>

  <!-- Footer -->
  <footer class="app-footer">
    Powered by AI · Responses may not capture every detail
    · <a href="${LINKEDIN_URL}" target="_blank" rel="noopener noreferrer" class="footer-link">Connect on LinkedIn</a> for direct contact
  </footer>
`;

// ── Element refs ──────────────────────────────────────────────
const messagesEl = document.getElementById('messages')!;
const suggestionsEl = document.getElementById('suggestions')!;
const inputEl = document.getElementById('chat-input') as HTMLTextAreaElement;
const sendBtn = document.getElementById('send-btn') as HTMLButtonElement;
const clearBtn = document.getElementById('clear-btn') as HTMLButtonElement;

// ── Helpers ───────────────────────────────────────────────────
function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function autoResize() {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
}

function updateSendBtn() {
  sendBtn.disabled = isTyping || !inputEl.value.trim();
}

function addMessage(role: 'user' | 'assistant', content: string) {
  const isUser = role === 'user';
  const div = document.createElement('div');
  div.className = `message ${isUser ? 'user' : 'bot'}`;
  div.innerHTML = `
    <div class="message-avatar">${isUser ? '👤' : '🤖'}</div>
    <div class="message-body">
      <span class="message-label">${isUser ? 'You' : 'Digital Twin'}</span>
      <div class="message-bubble">${escapeHtml(content)}</div>
    </div>
  `;
  messagesEl.appendChild(div);
  scrollToBottom();
}

function showTypingIndicator(): HTMLElement {
  const div = document.createElement('div');
  div.className = 'message bot';
  div.id = 'typing-indicator';
  div.innerHTML = `
    <div class="message-avatar">🤖</div>
    <div class="message-body">
      <span class="message-label">Digital Twin</span>
      <div class="message-bubble">
        <div class="typing-dots">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </div>
      </div>
    </div>
  `;
  messagesEl.appendChild(div);
  scrollToBottom();
  return div;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\n/g, '<br>');
}

// ── Send ──────────────────────────────────────────────────────
async function send(message: string) {
  if (!message.trim() || isTyping) return;

  // Hide suggestions after first message
  suggestionsEl.style.display = 'none';

  addMessage('user', message);
  history.push({ role: 'user', content: message });

  inputEl.value = '';
  autoResize();
  isTyping = true;
  updateSendBtn();

  const indicator = showTypingIndicator();

  try {
    const reply = await sendMessage(message, history.slice(0, -1));
    indicator.remove();
    addMessage('assistant', reply);
    history.push({ role: 'assistant', content: reply });
  } catch (err) {
    indicator.remove();
    addMessage('assistant', 'Sorry, something went wrong. Please try again.');
    console.error(err);
    // Remove the failed user message from history
    history.pop();
  } finally {
    isTyping = false;
    updateSendBtn();
  }
}

// ── Clear ─────────────────────────────────────────────────────
function clearConversation() {
  history = [];
  messagesEl.innerHTML = '';
  suggestionsEl.style.display = 'flex';
}

// ── Events ────────────────────────────────────────────────────
inputEl.addEventListener('input', () => {
  autoResize();
  updateSendBtn();
});

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    send(inputEl.value);
  }
});

sendBtn.addEventListener('click', () => send(inputEl.value));
clearBtn.addEventListener('click', clearConversation);

suggestionsEl.addEventListener('click', (e) => {
  const chip = (e.target as HTMLElement).closest('.suggestion-chip');
  if (chip instanceof HTMLElement) {
    send(chip.dataset.prompt ?? '');
  }
});

// ── Init ──────────────────────────────────────────────────────
inputEl.focus();
