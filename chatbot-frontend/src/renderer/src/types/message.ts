export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system' | 'error'
  content: string
  createdAt?: Date
}

