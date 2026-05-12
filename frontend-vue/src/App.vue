<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-inner">
        <div class="logo">
          <span class="logo-icon">🔗</span>
          <span class="logo-text">智链校园</span>
        </div>
        <nav class="agent-tabs">
          <button
            v-for="agent in agents"
            :key="agent.key"
            :class="['agent-btn', { active: activeAgent === agent.key }]"
            @click="activeAgent = agent.key"
          >
            <span class="agent-icon">{{ agent.icon }}</span>
            <span class="agent-label">{{ agent.label }}</span>
          </button>
        </nav>
      </div>
    </header>

    <main class="app-main">
      <ChatView
        :agent="activeAgent"
        @send="handleSend"
        :messages="messages"
        :loading="loading"
      />
    </main>

    <footer class="app-footer">
      <p>智链校园 2.0 · 基于 RAG 与多智能体协同的高校垂直领域全场景辅助平台</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ChatView from './components/ChatView.vue'
import { useChatStore } from './composables/chatStore'

const agents = [
  { key: 'academic', icon: '📚', label: '学术辅助' },
  { key: 'affairs', icon: '🏫', label: '校园事务' },
  { key: 'growth', icon: '🎯', label: '成长助手' },
]

const activeAgent = ref('affairs')
const loading = ref(false)

const chatStore = useChatStore()
const messages = ref(chatStore.messages)

async function handleSend(text: string) {
  loading.value = true
  const agentType = activeAgent.value

  // 添加用户消息
  messages.value.push({ role: 'user', content: text })

  // 使用 WebSocket 流式输出
  const aiMsg: { role: string; content: string } = { role: 'assistant', content: '' }
  messages.value.push(aiMsg)

  try {
    await streamChat(text, agentType, (chunk: string) => {
      aiMsg.content += chunk
    })
  } catch (err) {
    aiMsg.content = '网络错误，请稍后重试'
  } finally {
    loading.value = false
    chatStore.messages = messages.value
  }
}

async function streamChat(
  message: string,
  intent: string,
  onChunk: (chunk: string) => void
) {
  const ws = new WebSocket(
    `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/chat`
  )

  return new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(() => {
      ws.close()
      reject(new Error('超时'))
    }, 60000)

    ws.onopen = () => {
      ws.send(JSON.stringify({ message, intent, history: [] }))
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'chunk') {
          onChunk(data.content)
        } else if (data.type === 'done') {
          clearTimeout(timeout)
          ws.close()
          resolve()
        } else if (data.error) {
          clearTimeout(timeout)
          ws.close()
          reject(new Error(data.error))
        }
      } catch {
        // 非 JSON 数据直接作为内容
        onChunk(event.data)
      }
    }

    ws.onerror = () => {
      clearTimeout(timeout)
      reject(new Error('WebSocket 错误'))
    }

    ws.onclose = () => {
      clearTimeout(timeout)
      resolve()
    }
  })
}
</script>
