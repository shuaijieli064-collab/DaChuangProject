<template>
  <div class="chat-view">
    <!-- 快捷入口 -->
    <div v-if="messages.length <= 1" class="quick-entry">
      <h3 class="quick-title">快速开始</h3>
      <div class="quick-grid">
        <button
          v-for="item in quickItems"
          :key="item.text"
          class="quick-card"
          @click="$emit('send', item.text)"
        >
          <span class="quick-icon">{{ item.icon }}</span>
          <span class="quick-label">{{ item.label }}</span>
        </button>
      </div>
    </div>

    <!-- 消息列表 -->
    <div class="messages" ref="messagesRef">
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        :class="['message', msg.role === 'user' ? 'user-msg' : 'bot-msg']"
      >
        <span v-if="msg.role !== 'user'" class="msg-avatar">🤖</span>
        <div class="msg-content">
          <div v-if="msg.role === 'user'" class="msg-text">{{ msg.content }}</div>
          <div v-else class="msg-markdown" v-html="renderMarkdown(msg.content)"></div>
        </div>
      </div>
      <div v-if="loading" class="message bot-msg">
        <span class="msg-avatar">🤖</span>
        <div class="msg-content">
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入框 -->
    <div class="chat-input">
      <textarea
        v-model="inputText"
        :placeholder="placeholder"
        rows="2"
        @keydown.enter.exact.prevent="send"
        class="input-area"
      />
      <button class="send-btn" @click="send" :disabled="!inputText.trim() || loading">
        <el-icon><Promotion /></el-icon>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, computed } from 'vue'
import { Promotion } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import type { Message } from '../composables/chatStore'

const props = defineProps<{
  agent: string
  messages: Message[]
  loading: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
}>()

const inputText = ref('')
const messagesRef = ref<HTMLElement>()

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
})

function renderMarkdown(content: string) {
  return md.render(content)
}

function send() {
  const text = inputText.value.trim()
  if (!text || props.loading) return
  inputText.value = ''
  emit('send', text)
  nextTick(() => scrollToBottom())
}

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

watch(() => props.messages, () => nextTick(scrollToBottom), { deep: true })

const placeholder = computed(() => {
  const map: Record<string, string> = {
    academic: '输入课程内容、课件文字或知识点…',
    affairs: '如：请假流程、奖学金申请、证件补办…',
    growth: '如：学业规划建议、简历优化、面试训练…',
  }
  return map[props.agent] || '输入你的问题…'
})

const quickItems = computed(() => {
  const map: Record<string, { icon: string; label: string; text: string }[]> = {
    academic: [
      { icon: '📖', label: '知识点提炼', text: '请帮我提炼以下课件的核心知识点：\n\n' },
      { icon: '✏️', label: '生成练习题', text: '请根据以下内容生成练习题：\n\n' },
      { icon: '📅', label: '复习计划', text: '请为我制定复习计划，课程是：' },
      { icon: '📄', label: '文献综述', text: '请帮我构建以下主题的文献综述框架：' },
    ],
    affairs: [
      { icon: '🏥', label: '请假手续', text: '如何办理请假手续？请详细说明流程、材料和注意事项。' },
      { icon: '🏆', label: '奖学金申请', text: '奖学金申请流程是什么？需要什么材料和条件？' },
      { icon: '💰', label: '助学金申请', text: '助学金如何申请？需要什么证明材料？' },
      { icon: '🪪', label: '证件补办', text: '学生证丢失了如何补办？需要什么材料？' },
    ],
    growth: [
      { icon: '🗺️', label: '学业规划', text: '我是软件工程专业的学生，请为我提供学业和职业规划建议。' },
      { icon: '📄', label: '简历优化', text: '请帮我优化简历。我的简历内容如下：\n\n' },
      { icon: '🎤', label: '面试训练', text: '请为前端开发岗位生成10道常见面试题。' },
      { icon: '🧭', label: '校园导航', text: '请问图书馆怎么预约自习室？' },
    ],
  }
  return map[props.agent] || map.affairs
})
</script>
