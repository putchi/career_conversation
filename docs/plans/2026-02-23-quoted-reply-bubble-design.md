# Quoted Reply Bubble — Design

**Date:** 2026-02-23
**Status:** Approved

## Problem

When a user replies to a message, the reply context is sent to the AI as a text prefix (`[Replying to "..."]`) but the user's sent bubble shows no visual indication that it is a reply. WhatsApp shows a quoted preview block inside the bubble.

## Goal

Render a WhatsApp-style quoted snippet at the top of the user's message bubble whenever the message was sent as a reply.

## Visual Structure

```
┌─────────────────────────────────────────┐
│ ▌ Digital Twin                          │  colored bar + role name
│   "Sure, I worked at Acme Corp for..."  │  truncated quoted snippet
├─────────────────────────────────────────┤
│ That's interesting, tell me more        │  actual message text
└─────────────────────────────────────────┘
```

Bar and role-name color:
- Quoting assistant → `--accent` (purple)
- Quoting user → `--chat-user` (cyan)

## Approach

Option A: pass reply context as optional 3rd argument to `addMessage`.

### Data flow

1. `reply.ts` exposes `getActiveReply()` returning `{ role, content } | null`.
2. `send()` in `main.ts` grabs the snapshot **before** `clearReply()`:
   ```ts
   const replyContext = getActiveReply();
   clearReply();
   addMessage('user', message, replyContext);
   ```
3. `addMessage(role, content, replyContext?)` prepends a `.message-quote` block inside the bubble when `replyContext` is present.

The reply context is **display-only** — the API payload is unchanged (still uses the `[Replying to "..."]` text prefix).

## Files Changed

| File | Change |
|---|---|
| `frontend/src/reply.ts` | Add `getActiveReply()` export |
| `frontend/src/main.ts` | Optional 3rd param on `addMessage`; capture context in `send()` |
| `frontend/src/style.css` | New `.message-quote` block styles |
| `frontend/src/reply.test.ts` | 2 tests for `getActiveReply` |
| `frontend/src/main.test.ts` | Tests that quote block renders correctly |

## CSS

```css
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

.message-quote-role { font-size: 0.7rem; font-weight: 600; }
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

## Out of Scope

- Quote blocks in assistant bubbles (assistant doesn't reply to specific messages)
- Persisting quote context across page reloads
- Clicking the quote to scroll to the original message
