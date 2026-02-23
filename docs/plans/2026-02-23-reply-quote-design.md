# Reply / Quote Feature Design

**Date:** 2026-02-23
**Status:** Approved

## Summary

Add WhatsApp-style reply/quote functionality to chat messages. Users trigger a reply via swipe-right or long-press on mobile, or hover + click reply button on desktop. A reply banner appears above the input. On send, the quoted text is embedded as a prefix in the message sent to the AI, while the display bubble shows only the user's typed text.

## Requirements

- Both user and assistant messages are quotable
- Mobile triggers: swipe right **and** long press (both work)
- Desktop trigger: hover over message → click reply button (↩)
- Reply banner appears above the textarea (WhatsApp-style)
- Sending embeds `[Replying to "…"]\n\n` prefix in the API payload
- Display bubble shows only the user's typed words (not the prefix)
- Reply cleared automatically after send and on clear conversation
- 100% test coverage maintained

## Architecture

### New file: `frontend/src/reply.ts`

Owns all reply/quote concerns. `main.ts` calls into it; `reply.ts` never imports from `main.ts`.

**Exports:**

```typescript
initReply(inputArea: HTMLElement): void
attachReplyGestures(msgEl: HTMLElement, role: 'user' | 'assistant', content: string): void
showReplyBanner(role: 'user' | 'assistant', content: string): void
clearReply(): void
getReplyPrefix(): string | null
```

### New dependency

`hammerjs` + `@types/hammerjs` — handles swipe and long-press gesture recognition.

### `main.ts` changes (minimal)

- `initReply(inputAreaEl)` — called once during init
- `attachReplyGestures(msgEl, role, content)` — called at end of `addMessage()`
- `getReplyPrefix()` + `clearReply()` — called inside `send()` before API call

### No changes to `api.ts` or `Message` type

The quote prefix is plain text embedded in `content`.

## Gesture Detection

### Mobile — HammerJS

```typescript
const hammer = new Hammer(msgEl, {
  recognizers: [
    [Hammer.Swipe, { direction: Hammer.DIRECTION_RIGHT, threshold: 10, velocity: 0.3 }],
    [Hammer.Press, { time: 500 }],
  ]
});
hammer.on('swiperight press', () => showReplyBanner(role, content));
```

- `touchAction: 'pan-y'` preserved so vertical scrolling is unaffected
- On `panright` (partial swipe in progress): message bubble translates right up to 40px with a reply arrow fading in, springs back on release
- Long press (500ms): triggers reply, fires `navigator.vibrate(50)` if available

### Desktop — hover + reply button

Each message gets a `.reply-btn` (↩ icon) injected alongside `.message-bubble`:

```
.message
  ├── .message-avatar
  ├── .message-body
  │   ├── .message-label
  │   └── .message-bubble
  └── .reply-btn     ← new, hidden by default, shown on .message:hover
```

## Reply Banner UI

Lives inside `.input-area`, above the textarea. Hidden (`hidden` attribute) until activated.

```html
<div id="reply-banner" class="reply-banner" hidden>
  <div class="reply-banner-bar"></div>
  <div class="reply-banner-body">
    <span class="reply-banner-role">You</span>
    <span class="reply-banner-text">First 80 chars…</span>
  </div>
  <button class="reply-banner-close" aria-label="Cancel reply">✕</button>
</div>
```

**Styling:**
- Left accent bar: `var(--chat-user)` (cyan) for user quotes, `var(--accent)` (purple) for assistant quotes
- Background: glass surface matching input area
- Slide-in animation: `translateY` + `opacity`, ~150ms
- Role label in `JetBrains Mono`; text truncated with ellipsis

**Updated `.input-area` layout:**
```
.input-area
  ├── #reply-banner       ← new
  ├── textarea#chat-input
  ├── button#send-btn
  └── button#clear-btn
```

## Data Flow

### Init
```
initReply(inputAreaEl)
  → injects #reply-banner into DOM
  → binds ✕ button → clearReply()
```

### Per message render
```
addMessage(role, content)
  → creates .message div
  → attachReplyGestures(msgEl, role, content)
       → Hammer swiperight/press → showReplyBanner(role, content)
       → .reply-btn click → showReplyBanner(role, content)
```

### On send
```
send(rawInput)
  → prefix = getReplyPrefix()           // null if no active reply
  → fullMessage = prefix + rawInput     // or just rawInput
  → clearReply()                        // banner dismissed before API call
  → addMessage('user', rawInput)        // display: user's words only
  → sendMessage(fullMessage, history)   // AI sees full quoted prefix
  → history.push({ role:'user', content: fullMessage })
```

### Quote prefix format
```
[Replying to "…first 80 chars of quoted message…"]

{user's actual message here}
```

## Testing

### New file: `frontend/src/reply.test.ts`

| Test | Assertion |
|------|-----------|
| `getReplyPrefix()` returns null by default | No active reply |
| `getReplyPrefix()` returns correct format after `showReplyBanner()` | Prefix structure |
| Content truncated at 80 chars with `…` | Long message handling |
| `clearReply()` resets `getReplyPrefix()` to null | State reset |
| `showReplyBanner()` makes banner visible, sets role + text | DOM output |
| `clearReply()` hides banner | DOM output |
| `.reply-banner-bar` correct class for user vs assistant | Accent colour logic |
| ✕ button click calls `clearReply()` | Event binding |

### Updates to `main.test.ts`

| Test | Assertion |
|------|-----------|
| Sent message includes quote prefix when reply active | `sendMessage` called with prefix |
| Display bubble shows only raw user text | `.message-bubble` excludes prefix |
| Reply cleared after send | `getReplyPrefix()` null post-send |
| Reply cleared on clear conversation | `clearConversation()` also clears reply |

**Note on gesture tests:** jsdom doesn't support real touch events. `attachReplyGestures` is tested by directly invoking the `onReply` callback — the gesture wiring is a thin Hammer wrapper; the logic under test is `showReplyBanner`.

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/reply.ts` | **New** — all reply/quote logic |
| `frontend/src/reply.test.ts` | **New** — unit tests for reply.ts |
| `frontend/src/main.ts` | **Modified** — init, addMessage, send, clearConversation |
| `frontend/src/main.test.ts` | **Modified** — 4 new test cases |
| `frontend/src/style.css` | **Modified** — reply banner, reply-btn, swipe animation |
| `frontend/package.json` | **Modified** — add hammerjs, @types/hammerjs |
