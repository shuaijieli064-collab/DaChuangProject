import { ref } from 'vue'

export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export function useChatStore() {
  const messages = ref<Message[]>([
    {
      role: 'assistant',
      content: '你好！我是智链校园 AI 助手 👋\n\n我可以帮助你：\n- 📚 学术辅助：课件分析、练习题生成、复习计划\n- 🏫 校园事务：请假流程、奖学金申请、证件补办\n- 🎯 成长规划：学业规划、简历优化、面试训练\n\n请选择上方的 Agent 类型，然后告诉我你的需求。',
    },
  ])

  function clearMessages() {
    messages.value = []
  }

  return {
    messages,
    clearMessages,
  }
}
