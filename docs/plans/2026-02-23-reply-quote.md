# Reply / Quote Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add WhatsApp-style reply/quote to chat messages — swipe right or long press on mobile, hover + click reply button on desktop — with a banner above the input and the quote prefix embedded in the message sent to the AI.

**Architecture:** New `reply.ts` module owns all reply state, banner DOM, gesture wiring, and prefix formatting. `main.ts` calls into it at four points: init, addMessage, send, clearConversation. HammerJS handles swipe-right and long-press. The display bubble always shows only the user's raw text; the AI payload includes the `[Replying to "…"]` prefix.

**Tech Stack:** TypeScript, HammerJS (new runtime dep), `@types/hammerjs` (new dev dep), Vitest + jsdom.

---

### Task 1: Install HammerJS

**Files:**
- Modify: `frontend/package.json` (automatic via npm)

**Step 1: Install packages**

```bash
cd frontend && npm install hammerjs && npm install --save-dev @types/hammerjs
```

**Step 2: Verify TypeScript sees the types**

```bash
cd frontend && npx tsc --noEmit
```
Expected: no errors.

---

### Task 2: `reply.ts` — state, prefix, and banner DOM (TDD)

**Files:**
- Create: `frontend/src/reply.ts`
- Create: `frontend/src/reply.test.ts`

**Step 1: Write the failing tests**

Create `frontend/src/reply.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Hoist mock so reply.ts import of hammerjs gets the mock
vi.mock('hammerjs', () => {
  const Manager = vi.fn(() => ({ add: vi.fn(), on: vi.fn() }))
  const Swipe = vi.fn()
  const Press = vi.fn()
  const Pan = vi.fn()
  return { default: { Manager, Swipe, Press, Pan, DIRECTION_RIGHT: 4 } }
})

// ── getReplyPrefix / clearReply / showReplyBanner (no DOM) ────

describe('getReplyPrefix / clearReply', () => {
  let showReplyBanner: (role: 'user' | 'assistant', content: string) => void
  let clearReply: () => void
  let getReplyPrefix: () => string | null

  beforeEach(async () => {
    vi.resetModules()
    vi.mock('hammerjs', () => {
      const Manager = vi.fn(() => ({ add: vi.fn(), on: vi.fn() }))
      const Swipe = vi.fn()
      const Press = vi.fn()
      const Pan = vi.fn()
      return { default: { Manager, Swipe, Press, Pan, DIRECTION_RIGHT: 4 } }
    })
    const mod = await import('./reply.js')
    showReplyBanner = mod.showReplyBanner
    clearReply = mod.clearReply
    getReplyPrefix = mod.getReplyPrefix
  })

  it('returns null when no reply is active', () => {
    expect(getReplyPrefix()).toBeNull()
  })

  it('returns correct prefix after showReplyBanner', () => {
    showReplyBanner('assistant', 'Hello world')
    expect(getReplyPrefix()).toBe('[Replying to "Hello world"]\n\n')
  })

  it('truncates content at 80 chars', () => {
    const long = 'a'.repeat(100)
    showReplyBanner('user', long)
    expect(getReplyPrefix()).toBe(`[Replying to "${'a'.repeat(80)}…"]\n\n`)
  })

  it('returns null after clearReply', () => {
    showReplyBanner('user', 'test')
    clearReply()
    expect(getReplyPrefix()).toBeNull()
  })
})

// ── initReply / banner DOM ────────────────────────────────────

describe('initReply / banner DOM', () => {
  let mod: Awaited<ReturnType<typeof import('./reply.js')>>
  let inputArea: HTMLElement

  beforeEach(async () => {
    vi.resetModules()
    vi.mock('hammerjs', () => {
      const Manager = vi.fn(() => ({ add: vi.fn(), on: vi.fn() }))
      const Swipe = vi.fn()
      const Press = vi.fn()
      const Pan = vi.fn()
      return { default: { Manager, Swipe, Press, Pan, DIRECTION_RIGHT: 4 } }
    })
    mod = await import('./reply.js')
    inputArea = document.createElement('div')
    document.body.appendChild(inputArea)
    mod.initReply(inputArea)
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('injects #reply-banner into inputArea', () => {
    expect(inputArea.querySelector('#reply-banner')).not.toBeNull()
  })

  it('banner is hidden by default', () => {
    expect((inputArea.querySelector('#reply-banner') as HTMLElement).hidden).toBe(true)
  })

  it('showReplyBanner makes banner visible', () => {
    mod.showReplyBanner('assistant', 'Hello')
    expect((inputArea.querySelector('#reply-banner') as HTMLElement).hidden).toBe(false)
  })

  it('showReplyBanner sets role text to "Digital Twin" for assistant', () => {
    mod.showReplyBanner('assistant', 'Hello')
    expect(inputArea.querySelector('.reply-banner-role')!.textContent).toBe('Digital Twin')
  })

  it('showReplyBanner sets role text to "You" for user', () => {
    mod.showReplyBanner('user', 'Hello')
    expect(inputArea.querySelector('.reply-banner-role')!.textContent).toBe('You')
  })

  it('showReplyBanner sets snippet text', () => {
    mod.showReplyBanner('assistant', 'Hello world')
    expect(inputArea.querySelector('.reply-banner-text')!.textContent).toBe('Hello world')
  })

  it('banner bar has --user class when quoting user', () => {
    mod.showReplyBanner('user', 'hi')
    expect(inputArea.querySelector('.reply-banner-bar')!.classList.contains('reply-banner-bar--user')).toBe(true)
  })

  it('banner bar has --assistant class when quoting assistant', () => {
    mod.showReplyBanner('assistant', 'hi')
    expect(inputArea.querySelector('.reply-banner-bar')!.classList.contains('reply-banner-bar--assistant')).toBe(true)
  })

  it('clearReply hides the banner', () => {
    mod.showReplyBanner('user', 'test')
    mod.clearReply()
    expect((inputArea.querySelector('#reply-banner') as HTMLElement).hidden).toBe(true)
  })

  it('close button click hides the banner', () => {
    mod.showReplyBanner('user', 'test')
    ;(inputArea.querySelector('.reply-banner-close') as HTMLButtonElement).click()
    expect((inputArea.querySelector('#reply-banner') as HTMLElement).hidden).toBe(true)
  })
})

// ── attachReplyGestures ───────────────────────────────────────

describe('attachReplyGestures', () => {
  let mod: Awaited<ReturnType<typeof import('./reply.js')>>
  let HammerMock: { Manager: ReturnType<typeof vi.fn> }

  beforeEach(async () => {
    vi.resetModules()
    const Manager = vi.fn(() => ({ add: vi.fn(), on: vi.fn() }))
    HammerMock = { Manager }
    vi.mock('hammerjs', () => {
      const Swipe = vi.fn()
      const Press = vi.fn()
      const Pan = vi.fn()
      return { default: { Manager, Swipe, Press, Pan, DIRECTION_RIGHT: 4 } }
    })
    mod = await import('./reply.js')
    const inputArea = document.createElement('div')
    document.body.appendChild(inputArea)
    mod.initReply(inputArea)
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('injects .reply-btn into the message element', () => {
    const msgEl = document.createElement('div')
    mod.attachReplyGestures(msgEl, 'assistant', 'Hello')
    expect(msgEl.querySelector('.reply-btn')).not.toBeNull()
  })

  it('clicking .reply-btn activates reply state', () => {
    const msgEl = document.createElement('div')
    mod.attachReplyGestures(msgEl, 'assistant', 'Hello world')
    ;(msgEl.querySelector('.reply-btn') as HTMLButtonElement).click()
    expect(mod.getReplyPrefix()).toContain('Hello world')
  })

  it('constructs Hammer.Manager on the message element with pan-y touch action', async () => {
    const { default: Hammer } = await import('hammerjs')
    const msgEl = document.createElement('div')
    mod.attachReplyGestures(msgEl, 'user', 'test')
    expect(Hammer.Manager).toHaveBeenCalledWith(msgEl, expect.objectContaining({ touchAction: 'pan-y' }))
  })

  it('registers swiperight and press event handler on Hammer', async () => {
    const { default: Hammer } = await import('hammerjs')
    const mockOn = vi.fn()
    vi.mocked(Hammer.Manager).mockReturnValue({ add: vi.fn(), on: mockOn } as any)
    const msgEl = document.createElement('div')
    mod.attachReplyGestures(msgEl, 'user', 'test')
    expect(mockOn).toHaveBeenCalledWith('swiperight press', expect.any(Function))
  })
})
```

**Step 2: Run to verify tests fail**

```bash
cd frontend && npx vitest run src/reply.test.ts
```
Expected: many FAILs — `reply.ts` does not exist yet.

**Step 3: Create `frontend/src/reply.ts`**

```typescript
import Hammer from 'hammerjs'

interface ReplyContext {
  role: 'user' | 'assistant'
  content: string
}

let activeReply: ReplyContext | null = null
let bannerEl: HTMLElement | null = null
let bannerRoleEl: HTMLElement | null = null
let bannerTextEl: HTMLElement | null = null
let bannerBarEl: HTMLElement | null = null

function truncate(text: string): string {
  return text.length > 80 ? text.slice(0, 80) + '…' : text
}

export function getReplyPrefix(): string | null {
  if (!activeReply) return null
  return `[Replying to "${truncate(activeReply.content)}"]\n\n`
}

export function clearReply(): void {
  activeReply = null
  if (bannerEl) bannerEl.hidden = true
}

export function showReplyBanner(role: 'user' | 'assistant', content: string): void {
  activeReply = { role, content }
  if (!bannerEl || !bannerRoleEl || !bannerTextEl || !bannerBarEl) return
  bannerRoleEl.textContent = role === 'user' ? 'You' : 'Digital Twin'
  bannerTextEl.textContent = truncate(content)
  bannerBarEl.className = `reply-banner-bar reply-banner-bar--${role}`
  bannerEl.hidden = false
}

export function initReply(inputArea: HTMLElement): void {
  bannerEl = document.createElement('div')
  bannerEl.id = 'reply-banner'
  bannerEl.className = 'reply-banner'
  bannerEl.hidden = true

  bannerBarEl = document.createElement('div')
  bannerBarEl.className = 'reply-banner-bar'

  const body = document.createElement('div')
  body.className = 'reply-banner-body'

  bannerRoleEl = document.createElement('span')
  bannerRoleEl.className = 'reply-banner-role'

  bannerTextEl = document.createElement('span')
  bannerTextEl.className = 'reply-banner-text'

  const closeBtn = document.createElement('button')
  closeBtn.className = 'reply-banner-close'
  closeBtn.setAttribute('aria-label', 'Cancel reply')
  closeBtn.textContent = '✕'
  closeBtn.addEventListener('click', clearReply)

  body.append(bannerRoleEl, bannerTextEl)
  bannerEl.append(bannerBarEl, body, closeBtn)
  inputArea.prepend(bannerEl)
}

export function attachReplyGestures(
  msgEl: HTMLElement,
  role: 'user' | 'assistant',
  content: string
): void {
  // Desktop: reply button shown on CSS hover
  const replyBtn = document.createElement('button')
  replyBtn.className = 'reply-btn'
  replyBtn.setAttribute('aria-label', 'Reply')
  replyBtn.textContent = '↩'
  replyBtn.addEventListener('click', () => showReplyBanner(role, content))
  msgEl.appendChild(replyBtn)

  // Mobile: HammerJS swipe-right + long-press
  const mc = new Hammer.Manager(msgEl, { touchAction: 'pan-y' })
  mc.add([
    new Hammer.Swipe({ direction: Hammer.DIRECTION_RIGHT, threshold: 10, velocity: 0.3 }),
    new Hammer.Press({ time: 500 }),
    new Hammer.Pan({ direction: Hammer.DIRECTION_RIGHT, threshold: 10 }),
  ])

  const bubble = msgEl.querySelector('.message-bubble') as HTMLElement | null

  mc.on('swiperight press', () => {
    if ('vibrate' in navigator) navigator.vibrate(50)
    showReplyBanner(role, content)
  })

  mc.on('panright', (ev: HammerInput) => {
    if (!bubble) return
    bubble.style.transform = `translateX(${Math.min(ev.deltaX, 40)}px)`
  })

  mc.on('panend pancancel', () => {
    if (!bubble) return
    bubble.style.transform = ''
  })
}
```

**Step 4: Run reply tests**

```bash
cd frontend && npx vitest run src/reply.test.ts
```
Expected: all PASS.

**Step 5: Run full suite — no regressions**

```bash
cd frontend && npx vitest run
```
Expected: all existing tests PASS.

---

### Task 3: CSS — reply banner, reply button, swipe animation

**Files:**
- Modify: `frontend/src/style.css`

**Step 1: Check if `.message` already has `position: relative`**

Open `frontend/src/style.css` and search for the `.message` rule. If it does not have `position: relative`, add it. The `.reply-btn` is absolutely positioned inside `.message`.

**Step 2: Append CSS at the end of `style.css`**

```css
/* ─── Reply Banner ─────────────────────────────────────────── */

.reply-banner {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.5rem;
  background: hsla(220, 20%, 12%, 0.85);
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  animation: reply-banner-in 0.15s ease-out;
}

@keyframes reply-banner-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.reply-banner-bar {
  width: 3px;
  align-self: stretch;
  border-radius: 99px;
  flex-shrink: 0;
}

.reply-banner-bar--user      { background: var(--chat-user); }
.reply-banner-bar--assistant { background: var(--accent); }

.reply-banner-body {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  flex: 1;
  min-width: 0;
}

.reply-banner-role {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0.7;
}

.reply-banner-text {
  font-size: 0.8rem;
  opacity: 0.85;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.reply-banner-close {
  background: none;
  border: none;
  color: var(--foreground);
  opacity: 0.5;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  transition: opacity 0.15s;
  flex-shrink: 0;
}

.reply-banner-close:hover { opacity: 1; }

/* ─── Reply Button (desktop hover) ──────────────────────────── */

.message {
  position: relative;  /* needed for .reply-btn absolute positioning */
}

.reply-btn {
  position: absolute;
  top: 0.5rem;
  opacity: 0;
  background: hsla(220, 20%, 18%, 0.9);
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  color: var(--foreground);
  font-size: 0.85rem;
  cursor: pointer;
  padding: 0.2rem 0.4rem;
  transition: opacity 0.15s, background 0.15s;
  pointer-events: none;
}

/* User bubbles are right-aligned — put reply btn to their left */
.message.user .reply-btn { right: calc(100% - 2.5rem); }
/* Bot bubbles are left-aligned — put reply btn to their right */
.message.bot  .reply-btn { left: calc(100% - 2.5rem); }

.message:hover .reply-btn,
.message:focus-within .reply-btn {
  opacity: 1;
  pointer-events: auto;
}

.reply-btn:hover { background: hsla(220, 20%, 26%, 0.95); }

/* ─── Swipe spring-back ──────────────────────────────────────── */

.message-bubble {
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

**Step 3: Run full test suite — CSS changes should not break tests**

```bash
cd frontend && npx vitest run
```
Expected: all PASS.

---

### Task 4: Integrate into `main.ts` (TDD)

**Files:**
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/main.test.ts`

**Step 1: Add reply mock and new tests to `main.test.ts`**

At the top of `main.test.ts`, after the existing `mockSendMessage` declaration and `vi.mock('./api.js', ...)` block, add:

```typescript
const mockInitReply = vi.fn()
const mockAttachReplyGestures = vi.fn()
const mockGetReplyPrefix = vi.fn<[], string | null>().mockReturnValue(null)
const mockClearReply = vi.fn()

vi.mock('./reply.js', () => ({
  initReply: mockInitReply,
  attachReplyGestures: mockAttachReplyGestures,
  getReplyPrefix: mockGetReplyPrefix,
  clearReply: mockClearReply,
}))
```

In the `setup()` function, add resets for the new mocks (after `mockSendMessage.mockReset()`):

```typescript
async function setup(config = DEFAULT_CONFIG) {
  mockSendMessage.mockReset()
  mockGetReplyPrefix.mockReset()
  mockGetReplyPrefix.mockReturnValue(null)   // default: no active reply
  mockClearReply.mockReset()
  mockInitReply.mockReset()
  mockAttachReplyGestures.mockReset()
  vi.resetModules()
  document.body.innerHTML = '<div id="app"></div>'
  ;(window as any).CAREER_CONFIG = config
  await import('./main.js')
  return mockSendMessage
}
```

Add a new `describe` block at the end of `main.test.ts`:

```typescript
// ── Reply integration ─────────────────────────────────────────

describe('reply integration', () => {
  it('embeds quote prefix in message sent to API when reply is active', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('ok')
    mockGetReplyPrefix.mockReturnValue('[Replying to "Hello"]\n\n')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    input.value = 'tell me more'
    input.dispatchEvent(new Event('input'))
    document.getElementById('send-btn')!.click()

    await vi.waitFor(() => {
      expect(sendMessage).toHaveBeenCalledWith(
        '[Replying to "Hello"]\n\ntell me more',
        expect.any(Array)
      )
    })
  })

  it('display bubble shows only raw user text, not the prefix', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('ok')
    mockGetReplyPrefix.mockReturnValue('[Replying to "Hello"]\n\n')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    input.value = 'tell me more'
    input.dispatchEvent(new Event('input'))
    document.getElementById('send-btn')!.click()

    const bubble = document.querySelector('.message.user .message-bubble')!
    expect(bubble.textContent).toBe('tell me more')
    expect(bubble.textContent).not.toContain('[Replying to')
  })

  it('calls clearReply after sending', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('ok')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    input.value = 'hello'
    input.dispatchEvent(new Event('input'))
    document.getElementById('send-btn')!.click()

    await vi.waitFor(() => {
      expect(mockClearReply).toHaveBeenCalled()
    })
  })

  it('calls clearReply when clearing the conversation', async () => {
    await setup()
    document.getElementById('clear-btn')!.click()
    expect(mockClearReply).toHaveBeenCalled()
  })
})
```

**Step 2: Run to verify the 4 new tests fail**

```bash
cd frontend && npx vitest run src/main.test.ts
```
Expected: 4 FAIL (reply integration), all existing PASS.

**Step 3: Update `main.ts`**

**3a — Add import** (line 1, after the existing import):

```typescript
import { initReply, attachReplyGestures, getReplyPrefix, clearReply } from './reply.js'
```

**3b — Call `initReply`** (after line 213 `inputEl.focus()`):

```typescript
initReply(document.querySelector('.input-area') as HTMLElement)
```

**3c — Call `attachReplyGestures` in `addMessage`** (after `scrollToBottom()` on line 113):

```typescript
  messagesEl.appendChild(div);
  scrollToBottom();
  attachReplyGestures(div, role, content);   // ← add this line
```

**3d — Update `send()`** — replace the opening of the function (lines 149–156):

```typescript
async function send(message: string) {
  if (!message.trim() || isTyping) return;

  const prefix = getReplyPrefix();
  const fullMessage = prefix ? `${prefix}${message}` : message;
  clearReply();

  // Hide suggestions after first message
  suggestionsEl.style.display = 'none';

  addMessage('user', message);                              // display: raw text only
  history.push({ role: 'user', content: fullMessage });    // history + API: with prefix

  inputEl.value = '';
  autoResize();
  isTyping = true;
  updateSendBtn();

  const indicator = showTypingIndicator();

  try {
    const reply = await sendMessage(fullMessage, history.slice(0, -1));  // with prefix
```

(The rest of the `try/catch/finally` block is unchanged.)

**3e — Call `clearReply` in `clearConversation`** (line 183):

```typescript
function clearConversation() {
  clearReply();       // ← add this line
  history = [];
  messagesEl.innerHTML = '';
  suggestionsEl.style.display = 'flex';
}
```

**Step 4: Run the new tests**

```bash
cd frontend && npx vitest run src/main.test.ts
```
Expected: all PASS including the 4 new reply integration tests.

**Step 5: Run full suite**

```bash
cd frontend && npx vitest run
```
Expected: all PASS.

---

### Task 5: Coverage check + smoke test

**Step 1: Run coverage**

```bash
cd frontend && npm run test:coverage
```
Expected: 100% coverage across all files including `reply.ts`.

If coverage is below 100%, check the report (`frontend/coverage/index.html`) to see which lines are uncovered and add targeted tests.

**Step 2: Smoke test in browser**

```bash
./start.sh
```

Verify in browser at http://localhost:5173:

- **Desktop hover:** hover a message → `↩` button appears → click → reply banner slides in above input → type reply → send → bubble shows only typed text, suggestions gone → AI reply references the quoted message in context
- **Desktop ✕:** click ✕ on banner → banner dismisses, input unchanged
- **Mobile (DevTools device emulation):** swipe right on a message bubble → banner appears
- **Mobile long press:** hold finger on message 500ms → banner appears
- **Clear conversation:** click ↺ → banner dismisses if open, conversation resets

**Step 3: Commit**

```bash
git add frontend/src/reply.ts \
        frontend/src/reply.test.ts \
        frontend/src/main.ts \
        frontend/src/main.test.ts \
        frontend/src/style.css \
        frontend/package.json \
        frontend/package-lock.json \
        docs/plans/
git commit -m "feat: add WhatsApp-style reply/quote to chat messages

- New reply.ts: state, banner DOM, HammerJS gesture wiring
- Mobile: swipe-right + long-press (HammerJS); haptic vibrate on trigger
- Desktop: hover message → ↩ reply button
- Reply banner slides in above input with role-coloured accent bar
- Quote prefix embedded in API payload; display bubble shows raw text
- clearConversation also dismisses active reply
- 100% test coverage maintained

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
