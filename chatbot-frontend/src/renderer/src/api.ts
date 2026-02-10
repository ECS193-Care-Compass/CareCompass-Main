export type HelpType = 'medical' | 'emotional' | 'legal' | 'unsure'

export type ChatContext = {
  zip?: string
  helpType?: HelpType
  anonymous?: boolean
}

export type ChatResponse = {
  reply: string
  options: string[]
  safety: {
    crisis: boolean
    recommendHotline: boolean
    matched: string[]
  }
}

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080'
export const CHAT_ENDPOINT = `${API_BASE_URL}/chat`

export async function sendChatMessage(
  message: string,
  sessionId: string,
  context?: ChatContext
): Promise<ChatResponse> {
  const response = await fetch(CHAT_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sessionId,
      message,
      context
    })
  })

  if (!response.ok) {
    const errorText = await response.text().catch(() => '')
    throw new Error(errorText || `Backend error (${response.status})`)
  }

  return response.json()
}
