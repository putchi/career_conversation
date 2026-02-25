import { describe, it, expect, vi, beforeEach } from 'vitest'
import { sendMessage, type Message } from './api.js'

describe('sendMessage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('sends a POST request with session_id included', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ reply: 'Hello!' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await sendMessage('hi', [])

    const body = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(body.message).toBe('hi')
    expect(body.history).toEqual([])
    expect(typeof body.session_id).toBe('string')
    expect(body.session_id.length).toBeGreaterThan(0)
  })

  it('uses the same session_id across multiple calls', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ reply: 'ok' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await sendMessage('first', [])
    await sendMessage('second', [])

    const body1 = JSON.parse(mockFetch.mock.calls[0][1].body)
    const body2 = JSON.parse(mockFetch.mock.calls[1][1].body)
    expect(body1.session_id).toBe(body2.session_id)
  })

  it('returns the reply from the response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ reply: 'Great answer!' }),
    }))

    const result = await sendMessage('question', [])
    expect(result).toBe('Great answer!')
  })

  it('sends history in the request body', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ reply: 'ok' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    const history: Message[] = [
      { role: 'user', content: 'first' },
      { role: 'assistant', content: 'second' },
    ]
    await sendMessage('third', history)

    const body = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(body.message).toBe('third')
    expect(body.history).toEqual(history)
    expect(typeof body.session_id).toBe('string')
    expect(body.session_id.length).toBeGreaterThan(0)
  })

  it('throws an error when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    }))

    await expect(sendMessage('hi', [])).rejects.toThrow('HTTP 500: Internal Server Error')
  })

  it('throws with the correct status code in the message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    }))

    await expect(sendMessage('hi', [])).rejects.toThrow('HTTP 404')
  })
})
