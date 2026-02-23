import { describe, it, expect, vi } from 'vitest'

// Define mock function at module level so all imports share the same reference.
// vi.mock() is hoisted above this declaration, but the factory is called lazily
// (when the module is first imported), at which point mockSendMessage is initialized.
const mockSendMessage = vi.fn()

vi.mock('./api.js', () => ({
  sendMessage: mockSendMessage,
}))

const mockInitReply = vi.fn()
const mockAttachReplyGestures = vi.fn()
const mockGetReplyPrefix = vi.fn(() => null as string | null)
const mockClearReply = vi.fn()
const mockGetActiveReply = vi.fn(() => null as { role: 'user' | 'assistant'; content: string } | null)

vi.mock('./reply.js', () => ({
  initReply: mockInitReply,
  attachReplyGestures: mockAttachReplyGestures,
  getReplyPrefix: mockGetReplyPrefix,
  clearReply: mockClearReply,
  getActiveReply: mockGetActiveReply,
}))

const DEFAULT_CONFIG = {
  ownerName: 'Alex Rabinovich',
  ownerTitle: 'Software Engineer',
  linkedinUrl: 'https://linkedin.com/in/alex',
}

async function setup(config = DEFAULT_CONFIG) {
  mockSendMessage.mockReset()
  mockGetReplyPrefix.mockReset()
  mockGetReplyPrefix.mockReturnValue(null)
  mockClearReply.mockReset()
  mockInitReply.mockReset()
  mockAttachReplyGestures.mockReset()
  mockGetActiveReply.mockReset()
  mockGetActiveReply.mockReturnValue(null)
  vi.resetModules()
  document.body.innerHTML = '<div id="app"></div>'
  ;(window as any).CAREER_CONFIG = config
  await import('./main.js')
  return mockSendMessage
}

// ── Initialization ────────────────────────────────────────────

describe('initialization', () => {
  it('renders owner name in header', async () => {
    await setup()
    expect(document.querySelector('.header-title')?.textContent).toContain('Alex Rabinovich')
  })

  it('renders owner title as subtitle', async () => {
    await setup()
    expect(document.querySelector('.header-subtitle')?.textContent).toBe('Software Engineer')
  })

  it('uses first name from ownerName in textarea placeholder', async () => {
    await setup()
    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    expect(input.placeholder).toBe('Ask Alex anything...')
  })

  it('falls back to "me" in placeholder when ownerName is empty', async () => {
    await setup({ ownerName: '', ownerTitle: '', linkedinUrl: '' })
    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    expect(input.placeholder).toBe('Ask me anything...')
  })

  it('handles missing CAREER_CONFIG by using empty defaults', async () => {
    // Covers the `?? {}` branch on the CAREER_CONFIG null/undefined path
    mockSendMessage.mockReset()
    vi.resetModules()
    document.body.innerHTML = '<div id="app"></div>'
    delete (window as any).CAREER_CONFIG
    await import('./main.js')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    expect(input.placeholder).toBe('Ask me anything...')
  })

  it('renders linkedin URL in footer link', async () => {
    await setup()
    const link = document.querySelector('.footer-link') as HTMLAnchorElement
    expect(link.getAttribute('href')).toBe('https://linkedin.com/in/alex')
  })

  it('renders 4 suggestion chips', async () => {
    await setup()
    const chips = document.querySelectorAll('.suggestion-chip')
    expect(chips.length).toBe(4)
  })

  it('send button starts disabled', async () => {
    await setup()
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    expect(sendBtn.disabled).toBe(true)
  })

  it('focuses the chat input on load', async () => {
    await setup()
    expect(document.activeElement?.id).toBe('chat-input')
  })
})

// ── Input events ──────────────────────────────────────────────

describe('input events', () => {
  it('enables send button when text is entered', async () => {
    await setup()
    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement

    input.value = 'hello'
    input.dispatchEvent(new Event('input'))

    expect(sendBtn.disabled).toBe(false)
  })

  it('disables send button when input is only whitespace', async () => {
    await setup()
    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement

    input.value = '   '
    input.dispatchEvent(new Event('input'))

    expect(sendBtn.disabled).toBe(true)
  })

  it('disables send button after clearing input', async () => {
    await setup()
    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement

    input.value = 'hello'
    input.dispatchEvent(new Event('input'))
    input.value = ''
    input.dispatchEvent(new Event('input'))

    expect(sendBtn.disabled).toBe(true)
  })

  it('does not send on Enter+Shift (newline)', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('reply')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    input.value = 'hello'
    input.dispatchEvent(new Event('input'))

    const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, bubbles: true })
    input.dispatchEvent(event)

    await new Promise(r => setTimeout(r, 10))
    expect(sendMessage).not.toHaveBeenCalled()
  })
})

// ── Sending messages ──────────────────────────────────────────

describe('sending messages', () => {
  it('adds user message to the DOM', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('Reply!')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    input.value = 'Hello world'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    const bubbles = document.querySelectorAll('.message-bubble')
    expect(bubbles[0]?.textContent).toBe('Hello world')
  })

  it('adds assistant reply after successful send', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('Hello back!')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    input.value = 'Hi'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    await vi.waitFor(() => {
      const bubbles = document.querySelectorAll('.message-bubble')
      expect(bubbles.length).toBe(2)
    })

    const bubbles = document.querySelectorAll('.message-bubble')
    expect(bubbles[1]?.textContent).toBe('Hello back!')
  })

  it('clears input after sending', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('ok')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    input.value = 'message'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    expect(input.value).toBe('')
  })

  it('hides suggestions after first send', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('ok')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    input.value = 'hi'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    const suggestions = document.getElementById('suggestions') as HTMLElement
    expect(suggestions.style.display).toBe('none')
  })

  it('shows error message when sendMessage throws', async () => {
    const sendMessage = await setup()
    sendMessage.mockRejectedValue(new Error('Network error'))

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    input.value = 'hi'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    await vi.waitFor(() => {
      const bubbles = document.querySelectorAll('.message-bubble')
      expect(bubbles.length).toBe(2)
    })

    const bubbles = document.querySelectorAll('.message-bubble')
    expect(bubbles[1]?.textContent).toContain('went wrong')
  })

  it('removes failed user message from history on error', async () => {
    const sendMessage = await setup()
    sendMessage.mockRejectedValue(new Error('fail'))

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    input.value = 'hi'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    // Send again after error - history should not include the failed message
    await vi.waitFor(() => {
      const bubbles = document.querySelectorAll('.message-bubble')
      expect(bubbles.length).toBe(2)
    })

    sendMessage.mockResolvedValue('ok')
    input.value = 'retry'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    await vi.waitFor(() => {
      expect(sendMessage).toHaveBeenCalledTimes(2)
    })
    const [, historyArg] = sendMessage.mock.calls[1]
    expect(historyArg).toHaveLength(0)
  })

  it('does not send empty message when send button is clicked', async () => {
    const sendMessage = await setup()

    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    sendBtn.disabled = false
    sendBtn.click()

    await new Promise(r => setTimeout(r, 10))
    expect(sendMessage).not.toHaveBeenCalled()
  })

  it('ignores send while a message is already being sent', async () => {
    const sendMessage = await setup()
    let resolveFirst!: (v: string) => void
    sendMessage.mockReturnValueOnce(new Promise<string>(r => { resolveFirst = r }))

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    input.value = 'first'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    // Try to send while first is in-flight
    input.value = 'second'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    resolveFirst('done')
    await vi.waitFor(() => {
      expect(sendMessage).toHaveBeenCalledTimes(1)
    })
  })

  it('sends on Enter keydown', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('ok')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    input.value = 'hello'
    input.dispatchEvent(new Event('input'))

    const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: false, bubbles: true })
    input.dispatchEvent(event)

    await vi.waitFor(() => {
      expect(sendMessage).toHaveBeenCalledWith('hello', [])
    })
  })
})

// ── escapeHtml (tested via DOM output) ───────────────────────

describe('escapeHtml', () => {
  it('escapes & < > " \' and newlines in message content', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('ok')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    input.value = '<script>alert("xss")</script>'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    const bubble = document.querySelector('.message.user .message-bubble')!
    expect(bubble.innerHTML).not.toContain('<script>')
    expect(bubble.innerHTML).toContain('&lt;script&gt;')
  })

  it('renders newlines as <br> in message content', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('ok')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    input.value = 'line1\nline2'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    const bubble = document.querySelector('.message.user .message-bubble')!
    expect(bubble.innerHTML).toContain('<br>')
  })
})

// ── Clear conversation ────────────────────────────────────────

describe('clearConversation', () => {
  it('removes all messages from the DOM', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('reply')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    input.value = 'hi'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    await vi.waitFor(() => {
      expect(document.querySelectorAll('.message-bubble').length).toBe(2)
    })

    const clearBtn = document.getElementById('clear-btn') as HTMLButtonElement
    clearBtn.click()

    expect(document.querySelectorAll('.message').length).toBe(0)
  })

  it('shows suggestions again after clear', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('reply')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    input.value = 'hi'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    await vi.waitFor(() => {
      expect(document.querySelectorAll('.message-bubble').length).toBe(2)
    })

    const clearBtn = document.getElementById('clear-btn') as HTMLButtonElement
    clearBtn.click()

    const suggestions = document.getElementById('suggestions') as HTMLElement
    expect(suggestions.style.display).toBe('flex')
  })

  it('resets history so next message has no context', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('reply')

    const input = document.getElementById('chat-input') as HTMLTextAreaElement
    const sendBtn = document.getElementById('send-btn') as HTMLButtonElement
    input.value = 'first message'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    await vi.waitFor(() => expect(sendMessage).toHaveBeenCalledTimes(1))

    const clearBtn = document.getElementById('clear-btn') as HTMLButtonElement
    clearBtn.click()

    sendMessage.mockResolvedValue('second reply')
    input.value = 'second message'
    input.dispatchEvent(new Event('input'))
    sendBtn.click()

    await vi.waitFor(() => expect(sendMessage).toHaveBeenCalledTimes(2))
    const [, historyArg] = sendMessage.mock.calls[1]
    expect(historyArg).toHaveLength(0)
  })
})

// ── Suggestion chips ──────────────────────────────────────────

describe('suggestion chips', () => {
  it('sends the chip prompt when clicked', async () => {
    const sendMessage = await setup()
    sendMessage.mockResolvedValue('ok')

    const chip = document.querySelector('.suggestion-chip') as HTMLElement
    const prompt = chip.dataset.prompt!
    chip.click()

    await vi.waitFor(() => {
      expect(sendMessage).toHaveBeenCalledWith(prompt, [])
    })
  })

  it('clicking the suggestions container without a chip does nothing', async () => {
    const sendMessage = await setup()

    const suggestions = document.getElementById('suggestions') as HTMLElement
    suggestions.dispatchEvent(new MouseEvent('click', { bubbles: true }))

    await new Promise(r => setTimeout(r, 10))
    expect(sendMessage).not.toHaveBeenCalled()
  })

  it('chip without data-prompt attribute sends empty string (no-op)', async () => {
    // Covers the `chip.dataset.prompt ?? ''` fallback branch (line 208)
    const sendMessage = await setup()

    const suggestions = document.getElementById('suggestions') as HTMLElement
    const chip = document.createElement('button')
    chip.className = 'suggestion-chip'
    // Intentionally no data-prompt attribute
    suggestions.appendChild(chip)
    chip.click()

    await new Promise(r => setTimeout(r, 10))
    // send('') returns early without calling sendMessage
    expect(sendMessage).not.toHaveBeenCalled()
  })
})

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
})
