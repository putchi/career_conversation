# Quoted Reply Bubble Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Render a WhatsApp-style quoted snippet inside the user's message bubble when the message is sent as a reply.

**Architecture:** `reply.ts` exposes a new `getActiveReply()` export; `send()` in `main.ts` captures the context before `clearReply()` and passes it as an optional 3rd arg to `addMessage`, which injects a `.message-quote` block at the top of the bubble.

**Tech Stack:** TypeScript, Vitest (jsdom), Vite, CSS custom properties.

---

### Task 1: Add `getActiveReply()` to `reply.ts`

**Files:**
- Modify: `frontend/src/reply.ts`
- Test: `frontend/src/reply.test.ts`

**Step 1: Write the failing tests**

Add these two tests to the `initReply / banner DOM` describe block in `reply.test.ts`, after the existing `clearReply hides the banner` test:

```typescript
it('getActiveReply returns null when no reply is active', () => {
  expect(mod.getActiveReply()).toBeNull()
})

it('getActiveReply returns the active reply context after showReplyBanner', () => {
  mod.showReplyBanner('assistant', 'Hello world')
  expect(mod.getActiveReply()).toEqual({ role: 'assistant', content: 'Hello world' })
})
```

**Step 2: Run to verify they fail**

```bash
cd frontend && npx vitest run src/reply.test.ts
```

Expected: 2 FAILs — `mod.getActiveReply is not a function`

**Step 3: Implement `getActiveReply` in `reply.ts`**

Add this export after `clearReply`:

```typescript
export function getActiveReply(): { role: 'user' | 'assistant'; content: string } | null {
  return activeReply
}
```

**Step 4: Run to verify they pass**

```bash
cd frontend && npx vitest run src/reply.test.ts
```

Expected: all reply tests pass (was 28, now 30).

---

### Task 2: Update `main.test.ts` — add mock + failing tests

**Files:**
- Test: `frontend/src/main.test.ts`

**Step 1: Add `mockGetActiveReply` to the mock infrastructure**

At the top of `main.test.ts`, alongside the other mock declarations (around line 12), add:

```typescript
const mockGetActiveReply = vi.fn(() => null as { role: 'user' | 'assistant'; content: string } | null)
```

In the `vi.mock('./reply.js', ...)` factory, add the new mock (alongside the others):

```typescript
vi.mock('./reply.js', () => ({
  initReply: mockInitReply,
  attachReplyGestures: mockAttachReplyGestures,
  getReplyPrefix: mockGetReplyPrefix,
  clearReply: mockClearReply,
  getActiveReply: mockGetActiveReply,   // ← ADD
}))
```

In the `setup()` function, add a reset alongside the others:

```typescript
mockGetActiveReply.mockReset()
mockGetActiveReply.mockReturnValue(null)
```

**Step 2: Write the failing tests**

Add these tests to the existing `reply integration` describe block at the end of `main.test.ts`:

```typescript
it('renders quote block in bubble when reply context is active', async () => {
  const sendMessage = await setup()
  sendMessage.mockResolvedValue('ok')
  mockGetActiveReply.mockReturnValue({ role: 'assistant', content: 'Hello world' })

  const input = document.getElementById('chat-input') as HTMLTextAreaElement
  input.value = 'tell me more'
  input.dispatchEvent(new Event('input'))
  document.getElementById('send-btn')!.click()

  const bubble = document.querySelector('.message.user .message-bubble')!
  expect(bubble.querySelector('.message-quote')).not.toBeNull()
})

it('quote block shows "Digital Twin" for assistant context', async () => {
  const sendMessage = await setup()
  sendMessage.mockResolvedValue('ok')
  mockGetActiveReply.mockReturnValue({ role: 'assistant', content: 'Hello' })

  const input = document.getElementById('chat-input') as HTMLTextAreaElement
  input.value = 'reply'
  input.dispatchEvent(new Event('input'))
  document.getElementById('send-btn')!.click()

  expect(document.querySelector('.message.user .message-quote-role')!.textContent).toBe('Digital Twin')
})

it('quote block shows "You" for user context', async () => {
  const sendMessage = await setup()
  sendMessage.mockResolvedValue('ok')
  mockGetActiveReply.mockReturnValue({ role: 'user', content: 'my message' })

  const input = document.getElementById('chat-input') as HTMLTextAreaElement
  input.value = 'reply'
  input.dispatchEvent(new Event('input'))
  document.getElementById('send-btn')!.click()

  expect(document.querySelector('.message.user .message-quote-role')!.textContent).toBe('You')
})

it('quote block shows the quoted text snippet', async () => {
  const sendMessage = await setup()
  sendMessage.mockResolvedValue('ok')
  mockGetActiveReply.mockReturnValue({ role: 'assistant', content: 'Hello world snippet' })

  const input = document.getElementById('chat-input') as HTMLTextAreaElement
  input.value = 'reply'
  input.dispatchEvent(new Event('input'))
  document.getElementById('send-btn')!.click()

  expect(document.querySelector('.message.user .message-quote-text')!.textContent).toBe('Hello world snippet')
})

it('renders no quote block when no reply context', async () => {
  const sendMessage = await setup()
  sendMessage.mockResolvedValue('ok')
  // mockGetActiveReply returns null by default

  const input = document.getElementById('chat-input') as HTMLTextAreaElement
  input.value = 'hello'
  input.dispatchEvent(new Event('input'))
  document.getElementById('send-btn')!.click()

  const bubble = document.querySelector('.message.user .message-bubble')!
  expect(bubble.querySelector('.message-quote')).toBeNull()
})
```

**Step 3: Run to verify they fail**

```bash
cd frontend && npx vitest run src/main.test.ts
```

Expected: 4 FAILs (the "no quote block" test passes trivially; the four positive cases fail because `.message-quote` isn't rendered yet).

---

### Task 3: Implement changes in `main.ts`

**Files:**
- Modify: `frontend/src/main.ts`

**Step 1: Add `getActiveReply` to the import line**

Change line 2 of `main.ts` from:

```typescript
import { initReply, attachReplyGestures, getReplyPrefix, clearReply } from './reply.js';
```

to:

```typescript
import { initReply, attachReplyGestures, getReplyPrefix, clearReply, getActiveReply } from './reply.js';
```

**Step 2: Update `addMessage` to accept and render optional reply context**

Replace the existing `addMessage` function (around line 104) with:

```typescript
function addMessage(
  role: 'user' | 'assistant',
  content: string,
  replyContext?: { role: 'user' | 'assistant'; content: string } | null
) {
  const isUser = role === 'user';
  const div = document.createElement('div');
  div.className = `message ${isUser ? 'user' : 'bot'}`;

  const quoteHtml = replyContext ? (() => {
    const snippet = replyContext.content.length > 80
      ? replyContext.content.slice(0, 80) + '…'
      : replyContext.content;
    const roleName = replyContext.role === 'user' ? 'You' : 'Digital Twin';
    return `
      <div class="message-quote message-quote--${replyContext.role}">
        <div class="message-quote-bar"></div>
        <div class="message-quote-body">
          <span class="message-quote-role">${roleName}</span>
          <span class="message-quote-text">${escapeHtml(snippet)}</span>
        </div>
      </div>`;
  })() : '';

  div.innerHTML = `
    <div class="message-avatar">${isUser ? '👤' : '🤖'}</div>
    <div class="message-body">
      <span class="message-label">${isUser ? 'You' : 'Digital Twin'}</span>
      <div class="message-bubble">${quoteHtml}${escapeHtml(content)}</div>
    </div>
  `;
  messagesEl.appendChild(div);
  scrollToBottom();
  attachReplyGestures(div, role, content);
}
```

**Step 3: Capture reply context in `send()` before `clearReply()`**

In `send()`, replace:

```typescript
  const prefix = getReplyPrefix();
  const fullMessage = prefix ? `${prefix}${message}` : message;
  clearReply();

  // Hide suggestions after first message
  suggestionsEl.style.display = 'none';

  // display raw text only; fullMessage (with reply prefix) goes to history and API
  addMessage('user', message);
```

with:

```typescript
  const prefix = getReplyPrefix();
  const fullMessage = prefix ? `${prefix}${message}` : message;
  const replyContext = getActiveReply();
  clearReply();

  // Hide suggestions after first message
  suggestionsEl.style.display = 'none';

  // display raw text only; fullMessage (with reply prefix) goes to history and API
  addMessage('user', message, replyContext);
```

**Step 4: Run all tests**

```bash
cd frontend && npx vitest run
```

Expected: **74 tests pass** (was 67 + 2 reply + 5 main = 74). Zero failures.

---

### Task 4: Add CSS for `.message-quote`

**Files:**
- Modify: `frontend/src/style.css`

**Step 1: Add styles after the `/* ── Message ──` block** (after `.message.bot .message-bubble` around line 360)

```css
/* ── Quoted reply block (inside message bubble) ──────────── */
.message-quote {
  display: flex;
  gap: 0.5rem;
  border-radius: 0.375rem;
  padding: 0.375rem 0.5rem;
  margin-bottom: 0.375rem;
  background: hsla(0, 0%, 0%, 0.15);
}

.message-quote-bar {
  width: 3px;
  border-radius: 99px;
  align-self: stretch;
  flex-shrink: 0;
}

.message-quote--user .message-quote-bar     { background: var(--chat-user); }
.message-quote--assistant .message-quote-bar { background: var(--accent); }

.message-quote-body {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
  flex: 1;
}

.message-quote-role {
  font-size: 0.7rem;
  font-weight: 600;
}

.message-quote--user .message-quote-role     { color: var(--chat-user); }
.message-quote--assistant .message-quote-role { color: var(--accent); }

.message-quote-text {
  font-size: 0.75rem;
  color: var(--muted-foreground);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

**Step 2: Build to verify no errors**

```bash
cd frontend && npm run build
```

Expected: clean build, no TypeScript errors.

---

## Verification

```bash
cd frontend && npx vitest run    # 74 tests pass
cd frontend && npm run build     # clean
```

Smoke test in browser (`./start.sh` → localhost:5173):
1. Send a message, hover it, click ↩ → banner appears
2. Type a reply and send → user bubble shows quote block above the message text
3. Quote bar and role name are colored (cyan for user, purple for assistant)
4. Messages without a reply have no quote block
