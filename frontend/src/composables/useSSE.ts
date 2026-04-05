import { ref, onUnmounted } from 'vue'
import { useUserStore } from '../stores/useUserStore'

interface StateChange {
  from: string
  to: string
  progress: number
}

interface EmotionData {
  score: number
  label: string
}

export function useSSE() {
  const streaming = ref(false)
  const buffer = ref('')
  const stateChange = ref<StateChange | null>(null)
  const emotionData = ref<EmotionData | null>(null)
  const error = ref<string | null>(null)

  const userStore = useUserStore()

  function getToken() {
    return userStore.accessToken || localStorage.getItem('access_token')
  }

  let abortController: AbortController | null = null

  async function sendMessage(
    sessionId: string,
    content: string,
    onToken: (token: string) => void,
    onDone: (fullResponse: string) => void
  ) {
    streaming.value = true
    buffer.value = ''
    error.value = null
    stateChange.value = null
    emotionData.value = null
    
    abortController = new AbortController()
    
    try {
      const token = getToken()
      
      const response = await fetch(`/api/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: content,
        }),
        signal: abortController.signal,
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      
      if (data.content) {
        buffer.value = data.content
        onToken(data.content)
      }
      
      if (data.state) {
        stateChange.value = {
          from: '',
          to: data.state,
          progress: 0,
        }
      }
      
      if (data.emotion) {
        emotionData.value = {
          score: 0,
          label: data.emotion,
        }
      }
      
      onDone(buffer.value)
      
    } catch (e: any) {
      if (e.name === 'AbortError') {
        return
      }
      error.value = e.message || '发送失败'
      throw e
    } finally {
      streaming.value = false
      abortController = null
    }
  }
  
  async function sendMessageStream(
    sessionId: string,
    content: string,
    onToken: (token: string) => void,
    onDone: (fullResponse: string) => void
  ) {
    streaming.value = true
    buffer.value = ''
    error.value = null
    stateChange.value = null
    emotionData.value = null
    
    abortController = new AbortController()
    
    try {
      const token = getToken()
      
      const response = await fetch(`/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: content,
        }),
        signal: abortController.signal,
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No reader available')
      }
      
      const decoder = new TextDecoder()
      
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break
        
        const text = decoder.decode(value, { stream: true })
        const lines = text.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.token !== undefined) {
                buffer.value += data.token
                onToken(data.token)
              }

              if (data.state_change) {
                stateChange.value = data.state_change
              }

              // 后端 full_response 事件中携带 state 字段，更新步骤进度
              if (data.state !== undefined) {
                stateChange.value = {
                  from: stateChange.value?.to || 'GREETING',
                  to: data.state,
                  progress: 100,
                }
              }

              if (data.emotion) {
                emotionData.value = data.emotion
              }

              if (data.error) {
                error.value = data.error
              }

              if (data.full_response !== undefined) {
                streaming.value = false
                onDone(data.full_response)
              }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }
      
      if (streaming.value) {
        streaming.value = false
        onDone(buffer.value)
      }
      
    } catch (e: any) {
      if (e.name === 'AbortError') {
        return
      }
      error.value = e.message || '发送失败'
      throw e
    } finally {
      streaming.value = false
      abortController = null
    }
  }
  
  function cancel() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    streaming.value = false
  }
  
  onUnmounted(() => {
    cancel()
  })
  
  return {
    streaming,
    buffer,
    stateChange,
    emotionData,
    error,
    sendMessage,
    sendMessageStream,
    cancel,
  }
}
