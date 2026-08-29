<template>
  <div class="chat-container">
    <div class="chat-header">
      <div class="header-left">
        <h2>AI 反诈助手</h2>
        <div class="session-info" v-if="sessionId">
          <span class="session-id">{{ sessionId.substring(0, 12) }}...</span>
        </div>
      </div>
      <div class="header-actions">
        <button @click="showHistory = !showHistory" class="btn-icon" title="会话历史">
          <span><el-icon><Files /></el-icon></span>
        </button>
        <button @click="newSession" class="btn-icon" title="新会话">
          <span>➕</span>
        </button>
        <button @click="clearSession" class="btn-icon btn-danger" title="清空对话">
          <span><el-icon><Delete /></el-icon></span>
        </button>
      </div>
    </div>

    <!-- 会话历史侧边栏 -->
    <div v-if="showHistory" class="history-sidebar">
      <div class="history-header">
        <h3>会话历史</h3>
        <button @click="showHistory = false" class="btn-close">×</button>
      </div>
      <div class="history-list">
        <div v-if="sessions.length === 0" class="no-sessions">
          暂无历史会话
        </div>
        <div
          v-for="session in sessions"
          :key="session.id"
          :class="['history-item', { active: session.id === sessionId }]"
          @click="loadSession(session.id)"
        >
          <div class="session-title">{{ session.title || '未命名会话' }}</div>
          <div class="session-meta">
            <span>{{ session.messageCount }} 条消息</span>
            <span>{{ formatTime(session.lastActive) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-main">
      <div class="chat-messages" ref="messagesContainer">
        <div v-if="messages.length === 0" class="welcome-message">
          <h3>欢迎使用 AI 反诈助手</h3>
          <p class="welcome-desc">我可以帮助您分析诈骗案件、查询相关信息、提供防范建议</p>
          
          <div class="quick-actions">
            <h4>快速开始</h4>
            <div class="action-grid">
              <button
                v-for="action in quickActions"
                :key="action.label"
                @click="executeQuickAction(action)"
                class="action-card"
              >
                <div class="action-icon">{{ action.icon }}</div>
                <div class="action-label">{{ action.label }}</div>
                <div class="action-desc">{{ action.description }}</div>
              </button>
            </div>
          </div>

          <div class="example-queries">
            <h4>试试这些问题</h4>
            <div class="query-list">
              <button
                v-for="query in exampleQueries"
                :key="query"
                @click="userInput = query"
                class="query-item"
              >
                {{ query }}
              </button>
            </div>
          </div>
        </div>

        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message', msg.role, { streaming: msg.isStreaming }]"
        >
          <div class="message-avatar">
            <span v-if="msg.role === 'user'"><el-icon><User /></el-icon></span>
            <span v-else><el-icon><Cpu /></el-icon></span>
          </div>
          <div class="message-content">
            <!-- 工具调用状态 -->
            <div v-if="msg.metadata && msg.metadata.tool_status" class="tool-status">
              <span class="tool-status-icon">⚙️</span>
              <span class="tool-status-text">{{ msg.metadata.tool_status }}</span>
            </div>
            
            <!-- 消息内容 -->
            <div class="message-text-wrapper">
              <div class="message-text" v-html="formatMessage(msg.content)"></div>
              <!-- 流式打字光标 -->
              <span v-if="msg.isStreaming && msg.content" class="typing-cursor">▋</span>
            </div>
            
            <!-- 空内容时的加载指示 -->
            <div v-if="msg.isStreaming && !msg.content" class="streaming-placeholder">
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
            
            <div class="message-meta" v-if="msg.metadata && (msg.metadata.intent || msg.metadata.tool_used)">
              <span v-if="msg.metadata.intent" class="meta-tag intent">
                <el-icon><Aim /></el-icon> {{ msg.metadata.intent }}
              </span>
              <span v-if="msg.metadata.tool_used" class="meta-tag tool">
                <el-icon><Tools /></el-icon> {{ msg.metadata.tool_used }}
              </span>
              <span v-if="msg.metadata.duration_seconds" class="meta-tag duration">
                ⏱️ {{ msg.metadata.duration_seconds.toFixed(2) }}s
              </span>
            </div>
            <div class="message-time">
              {{ formatTime(msg.timestamp) }}
            </div>
          </div>
        </div>

        <div v-if="isLoading" class="message assistant loading">
          <div class="message-avatar"><el-icon><Cpu /></el-icon></div>
          <div class="message-content">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>

      <div class="chat-input-area">
        <div class="input-wrapper">
          <textarea
            v-model="userInput"
            @keydown.enter.exact="sendMessage"
            @input="adjustTextareaHeight"
            ref="inputTextarea"
            placeholder="输入您的问题... (Enter 发送, Shift+Enter 换行)"
            rows="1"
            :disabled="isLoading"
          ></textarea>
          <button
            @click="sendMessage"
            :disabled="!userInput.trim() || isLoading"
            class="btn-send"
          >
            <span v-if="!isLoading">发送</span>
            <span v-else>处理中...</span>
          </button>
        </div>
        <div class="input-footer">
          <div class="input-hints">
            <span class="hint-text"><el-icon><InfoFilled /></el-icon> 支持查询案件、搜索相似案例、统计分析、知识库检索</span>
          </div>
          <div class="input-actions">
            <button @click="showShortcuts = !showShortcuts" class="btn-shortcut" title="快捷指令">
              ⌨️
            </button>
          </div>
        </div>

        <!-- 快捷指令面板 -->
        <div v-if="showShortcuts" class="shortcuts-panel">
          <div class="shortcut-item" v-for="shortcut in shortcuts" :key="shortcut.command" @click="useShortcut(shortcut)">
            <span class="shortcut-command">{{ shortcut.command }}</span>
            <span class="shortcut-desc">{{ shortcut.description }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-toast">
      <span class="error-icon">⚠️</span>
      <span class="error-text">{{ error }}</span>
      <button @click="error = null" class="btn-close-error">×</button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, nextTick, watch, computed } from 'vue';
import api from '../api';
import { store } from '../store.js';

export default {
  name: 'ChatView',
  setup() {
    const messages = ref([]);
    const userInput = ref('');
    const isLoading = ref(false);
    const sessionId = ref(null);
    const error = ref(null);
    const messagesContainer = ref(null);
    const inputTextarea = ref(null);
    const showHistory = ref(false);
    const showShortcuts = ref(false);
    const sessions = ref([]);

    // 快捷操作
    const quickActions = [
      {
        icon: '📊',
        label: '查询案件',
        description: '查看最近的案件列表',
        command: '查询最近的10个案件'
      },
      {
        icon: '🔍',
        label: '相似案件',
        description: '搜索相似案件',
        command: '搜索与冒充公检法诈骗相似的案件'
      },
      {
        icon: '📈',
        label: '统计分析',
        description: '查看案件统计数据',
        command: '这个月的案件统计'
      },
      {
        icon: '📚',
        label: '反诈知识',
        description: '搜索反诈知识库',
        command: '冒充公检法诈骗的特征是什么'
      }
    ];

    // 示例问题
    const exampleQueries = [
      '查询最近的高风险案件',
      '搜索刷单诈骗的相似案件',
      '这个月的案件统计',
      '杀猪盘诈骗有什么特征',
      '如何防范电信诈骗'
    ];

    // 快捷指令
    const shortcuts = [
      { command: '/cases', description: '查询案件列表' },
      { command: '/stats', description: '查看统计数据' },
      { command: '/search', description: '搜索相似案件' },
      { command: '/knowledge', description: '搜索知识库' }
    ];

    // 增强的Markdown格式化
    const formatMessage = (content) => {
      if (!content) return '';
      
      let formatted = content;
      
      // 代码块 ```code```
      formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre class="code-block"><code class="language-${lang || 'text'}">${escapeHtml(code.trim())}</code></pre>`;
      });
      
      // 行内代码 `code`
      formatted = formatted.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
      
      // 粗体 **text**
      formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      
      // 斜体 *text*
      formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
      
      // 链接 [text](url)
      formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
      
      // 无序列表
      formatted = formatted.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
      formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
      
      // 有序列表
      formatted = formatted.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
      
      // 标题
      formatted = formatted.replace(/^### (.+)$/gm, '<h3>$1</h3>');
      formatted = formatted.replace(/^## (.+)$/gm, '<h2>$1</h2>');
      formatted = formatted.replace(/^# (.+)$/gm, '<h1>$1</h1>');
      
      // 换行
      formatted = formatted.replace(/\n/g, '<br>');
      
      return formatted;
    };

    const escapeHtml = (text) => {
      const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
      };
      return text.replace(/[&<>"']/g, m => map[m]);
    };

    const formatTime = (timestamp) => {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      const now = new Date();
      const diff = now - date;
      
      if (diff < 60000) return '刚刚';
      if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
      if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
      
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    };

    const adjustTextareaHeight = () => {
      const textarea = inputTextarea.value;
      if (textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
      }
    };

    const scrollToBottom = () => {
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
        }
      });
    };

    const sendMessage = async (e) => {
      if (e && e.shiftKey) return;
      if (e) e.preventDefault();

      const message = userInput.value.trim();
      if (!message || isLoading.value) return;

      messages.value.push({
        role: 'user',
        content: message,
        timestamp: new Date().toISOString()
      });

      userInput.value = '';
      adjustTextareaHeight();
      isLoading.value = true;
      error.value = null;
      scrollToBottom();

      // 添加助手消息占位符（用于流式更新）
      const assistantMessage = {
        role: 'assistant',
        content: '',
        metadata: {},
        timestamp: new Date().toISOString(),
        isStreaming: true
      };
      messages.value.push(assistantMessage);

      try {
        // 使用 fetch API 读取 SSE 流
        // 注意：token 存在 sessionStorage（键 fraudlens_token），由 store 统一维护。
        // 此前误读 localStorage.getItem('token')，永远为 null → 后端 401
        const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:5003';
        const token = store.token;
        
        const response = await fetch(`${API_BASE}/api/chat/message/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
          },
          body: JSON.stringify({
            message: message,
            session_id: sessionId.value
          })
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          
          // 解析 SSE 事件
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // 保留未完成的行

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const eventData = JSON.parse(line.slice(6));
                
                // 处理不同类型的事件
                switch (eventData.type) {
                  case 'intent':
                    assistantMessage.metadata.intent = eventData.content;
                    break;
                  
                  case 'tool_start':
                    assistantMessage.metadata.tool_status = `正在调用: ${eventData.content}`;
                    break;
                  
                  case 'tool_end':
                    assistantMessage.metadata.tool_status = eventData.content;
                    break;
                  
                  case 'token':
                    // 流式追加文本内容
                    assistantMessage.content += eventData.content;
                    scrollToBottom();
                    break;
                  
                  case 'done':
                    assistantMessage.isStreaming = false;
                    if (eventData.metadata) {
                      assistantMessage.metadata = {
                        ...assistantMessage.metadata,
                        ...eventData.metadata
                      };
                      if (eventData.metadata.session_id) {
                        sessionId.value = eventData.metadata.session_id;
                        updateSessionInfo(eventData.metadata.session_id, message);
                      }
                    }
                    break;
                  
                  case 'error':
                    assistantMessage.content += `\n\n[错误] ${eventData.content}`;
                    assistantMessage.isStreaming = false;
                    break;
                }
                
                // 触发响应式更新
                messages.value = [...messages.value];
                
              } catch (parseError) {
                console.warn('Failed to parse SSE event:', parseError, line);
              }
            }
          }
        }

        // 确保流结束标记
        assistantMessage.isStreaming = false;
        messages.value = [...messages.value];

      } catch (err) {
        console.error('Chat stream error:', err);
        error.value = err.message || '发送消息失败，请重试';
        
        // 更新助手消息为错误提示
        assistantMessage.content = '抱歉，处理您的消息时出现了问题。请稍后再试。';
        assistantMessage.isStreaming = false;
        messages.value = [...messages.value];
      } finally {
        isLoading.value = false;
        scrollToBottom();
      }
    };

    const executeQuickAction = (action) => {
      userInput.value = action.command;
      sendMessage();
    };

    const useShortcut = (shortcut) => {
      userInput.value = shortcut.command + ' ';
      inputTextarea.value?.focus();
      showShortcuts.value = false;
    };

    const newSession = () => {
      sessionId.value = null;
      messages.value = [];
      error.value = null;
    };

    const clearSession = async () => {
      if (!sessionId.value) {
        messages.value = [];
        return;
      }

      if (!confirm('确定要清空当前对话吗？')) return;

      try {
        await api.delete(`/api/chat/sessions/${sessionId.value}`);
        messages.value = [];
        sessionId.value = null;
        error.value = null;
      } catch (err) {
        console.error('Clear session error:', err);
        error.value = '清空对话失败';
      }
    };

    const loadSession = async (sessionIdToLoad) => {
      try {
        const response = await api.get(`/api/chat/sessions/${sessionIdToLoad}/history`);
        const data = response.data;
        
        sessionId.value = sessionIdToLoad;
        messages.value = data.messages || [];
        showHistory.value = false;
        scrollToBottom();
      } catch (err) {
        console.error('Load session error:', err);
        error.value = '加载会话失败';
      }
    };

    const updateSessionInfo = (sessionId, firstMessage) => {
      const existingIndex = sessions.value.findIndex(s => s.id === sessionId);
      if (existingIndex >= 0) {
        sessions.value[existingIndex].messageCount++;
        sessions.value[existingIndex].lastActive = new Date().toISOString();
        if (!sessions.value[existingIndex].title) {
          sessions.value[existingIndex].title = firstMessage.substring(0, 20);
        }
      } else {
        sessions.value.unshift({
          id: sessionId,
          title: firstMessage.substring(0, 20),
          messageCount: 1,
          lastActive: new Date().toISOString()
        });
      }
    };

    watch(messages, () => {
      scrollToBottom();
    }, { deep: true });

    onMounted(() => {
      adjustTextareaHeight();
    });

    return {
      messages,
      userInput,
      isLoading,
      sessionId,
      error,
      messagesContainer,
      inputTextarea,
      showHistory,
      showShortcuts,
      sessions,
      quickActions,
      exampleQueries,
      shortcuts,
      formatMessage,
      formatTime,
      adjustTextareaHeight,
      sendMessage,
      executeQuickAction,
      useShortcut,
      newSession,
      clearSession,
      loadSession
    };
  }
};
</script>

<style scoped>
.chat-container {
  display: flex;
  height: calc(100vh - 80px);
  background: transparent;
  position: relative;
  overflow: hidden;
}

.chat-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: rgba(10, 14, 26, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-primary);
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.3);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.chat-header h2 {
  margin: 0;
  font-size: 20px;
  color: var(--text-primary);
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 700;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-icon {
  padding: 8px 12px;
  background: rgba(0, 198, 255, 0.08);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.3s;
  color: var(--text-secondary);
}

.btn-icon:hover {
  background: rgba(0, 198, 255, 0.15);
  border-color: var(--border-secondary);
  box-shadow: 0 0 12px rgba(0, 198, 255, 0.1);
}

.btn-icon.btn-danger:hover {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.4);
}

.session-info {
  font-size: 12px;
  color: var(--text-muted);
  padding: 4px 10px;
  background: rgba(0, 198, 255, 0.06);
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  font-family: 'SF Mono', 'Consolas', monospace;
}

/* 历史侧边栏 */
.history-sidebar {
  position: absolute;
  top: 0;
  right: 0;
  width: 320px;
  height: 100%;
  background: rgba(10, 14, 26, 0.95);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-left: 1px solid var(--border-primary);
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.4);
  z-index: 20;
  display: flex;
  flex-direction: column;
  animation: slideInRight 0.3s ease;
}

@keyframes slideInRight {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-primary);
  background: rgba(0, 0, 0, 0.2);
}

.history-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
  font-weight: 600;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-muted);
  transition: color 0.3s;
}

.btn-close:hover {
  color: var(--accent-cyan);
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.no-sessions {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
  font-size: 14px;
}

.history-item {
  padding: 12px 16px;
  margin-bottom: 8px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid transparent;
  background: rgba(0, 0, 0, 0.2);
}

.history-item:hover {
  background: rgba(0, 198, 255, 0.08);
  border-color: var(--border-primary);
}

.history-item.active {
  background: rgba(0, 198, 255, 0.12);
  border: 1px solid var(--border-secondary);
  box-shadow: 0 0 16px rgba(0, 198, 255, 0.08);
}

.session-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.session-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-muted);
}

/* 主内容区 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-top: 73px;
  height: calc(100vh - 80px - 73px);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  scroll-behavior: smooth;
}

/* 欢迎页面 */
.welcome-message {
  text-align: center;
  padding: 40px 20px;
  max-width: 800px;
  margin: 0 auto;
  animation: fadeInUp 0.6s ease;
}

.welcome-message h3 {
  color: var(--text-primary);
  margin-bottom: 12px;
  font-size: 26px;
  font-weight: 700;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.welcome-desc {
  color: var(--text-secondary);
  margin-bottom: 32px;
  font-size: 14px;
}

.quick-actions {
  margin-bottom: 32px;
}

.quick-actions h4 {
  color: var(--text-primary);
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.action-card {
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  text-align: center;
  position: relative;
  overflow: hidden;
}

.action-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--gradient-primary);
  opacity: 0;
  transition: opacity 0.3s;
}

.action-card:hover {
  border-color: var(--border-secondary);
  box-shadow: 0 8px 24px rgba(0, 198, 255, 0.15);
  transform: translateY(-4px);
}

.action-card:hover::before {
  opacity: 1;
}

.action-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.action-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.action-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.example-queries h4 {
  color: var(--text-primary);
  margin-bottom: 12px;
  font-size: 16px;
  font-weight: 600;
}

.query-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.query-item {
  padding: 8px 16px;
  background: rgba(0, 198, 255, 0.06);
  border: 1px solid var(--border-primary);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 13px;
  color: var(--text-secondary);
}

.query-item:hover {
  background: rgba(0, 198, 255, 0.12);
  border-color: var(--border-secondary);
  color: var(--accent-cyan);
  box-shadow: 0 0 12px rgba(0, 198, 255, 0.1);
}

/* 消息样式 */
.message {
  display: flex;
  margin-bottom: 20px;
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  font-size: 32px;
  margin: 0 12px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.message-content {
  max-width: 70%;
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transition: all 0.3s;
}

.message-content:hover {
  border-color: var(--border-secondary);
  box-shadow: 0 6px 20px rgba(0, 198, 255, 0.08);
}

.message.user .message-content {
  background: linear-gradient(135deg, rgba(0, 132, 255, 0.25) 0%, rgba(0, 198, 255, 0.15) 100%);
  border: 1px solid var(--border-secondary);
  color: var(--text-primary);
  box-shadow: 0 4px 16px rgba(0, 198, 255, 0.15);
}

.message-text {
  line-height: 1.6;
  word-wrap: break-word;
  color: var(--text-primary);
}

.message-text :deep(code) {
  background: rgba(0, 198, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 0.9em;
  color: var(--accent-cyan);
  border: 1px solid rgba(0, 198, 255, 0.15);
}

.message-text :deep(pre.code-block) {
  background: rgba(0, 0, 0, 0.4);
  color: var(--text-primary);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
  border: 1px solid var(--border-primary);
}

.message-text :deep(pre.code-block code) {
  background: none;
  padding: 0;
  color: inherit;
  border: none;
}

.message.user .message-text :deep(code) {
  background: rgba(255, 255, 255, 0.15);
  color: var(--text-primary);
  border-color: rgba(255, 255, 255, 0.2);
}

.message-meta {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.2);
  color: var(--text-secondary);
  border: 1px solid var(--border-primary);
}

.message.user .meta-tag {
  background: rgba(255, 255, 255, 0.15);
  color: var(--text-primary);
  border-color: rgba(255, 255, 255, 0.2);
}

.meta-tag.intent {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.3);
}

.meta-tag.tool {
  background: rgba(0, 198, 255, 0.15);
  color: var(--accent-cyan);
  border-color: rgba(0, 198, 255, 0.3);
}

.meta-tag.duration {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.3);
}

.message.user .meta-tag.intent,
.message.user .meta-tag.tool,
.message.user .meta-tag.duration {
  background: rgba(255, 255, 255, 0.2);
  color: var(--text-primary);
  border-color: rgba(255, 255, 255, 0.3);
}

.message-time {
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-muted);
}

.message.user .message-time {
  color: rgba(255, 255, 255, 0.6);
}

/* 加载动画 */
.loading .typing-indicator,
.streaming-placeholder .typing-indicator {
  display: flex;
  gap: 6px;
  padding: 8px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: var(--accent-cyan);
  border-radius: 50%;
  animation: typing 1.4s infinite;
  box-shadow: 0 0 8px rgba(0, 198, 255, 0.4);
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

/* 流式输出样式 */
.message.streaming {
  animation: fadeIn 0.3s ease-in, pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}

.typing-cursor {
  display: inline-block;
  color: var(--accent-cyan);
  animation: blink 1s step-end infinite;
  margin-left: 2px;
  font-weight: bold;
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  50.01%, 100% {
    opacity: 0;
  }
}

.tool-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 8px;
  background: rgba(0, 198, 255, 0.08);
  border: 1px solid rgba(0, 198, 255, 0.2);
  border-radius: 8px;
  font-size: 13px;
  color: var(--accent-cyan);
  animation: slideInLeft 0.3s ease;
}

@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.tool-status-icon {
  font-size: 14px;
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.tool-status-text {
  font-weight: 500;
}

/* 输入区域 */
.chat-input-area {
  padding: 16px 24px;
  background: rgba(10, 14, 26, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid var(--border-primary);
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.3);
  position: relative;
}

.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-wrapper textarea {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  overflow: hidden;
  transition: all 0.3s;
  background: rgba(0, 0, 0, 0.3);
  color: var(--text-primary);
}

.input-wrapper textarea:focus {
  outline: none;
  border-color: var(--accent-cyan);
  box-shadow: 0 0 12px rgba(0, 198, 255, 0.15);
}

.input-wrapper textarea:disabled {
  background: rgba(0, 0, 0, 0.4);
  cursor: not-allowed;
  opacity: 0.6;
}

.input-wrapper textarea::placeholder {
  color: var(--text-muted);
}

.btn-send {
  padding: 12px 24px;
  background: var(--gradient-primary);
  color: var(--bg-primary);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;
  white-space: nowrap;
  box-shadow: 0 4px 12px rgba(0, 198, 255, 0.2);
}

.btn-send:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(0, 198, 255, 0.4);
  transform: translateY(-2px);
}

.btn-send:disabled {
  background: rgba(100, 116, 139, 0.3);
  color: var(--text-muted);
  cursor: not-allowed;
  box-shadow: none;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.input-hints {
  flex: 1;
}

.hint-text {
  font-size: 12px;
  color: var(--text-muted);
}

.input-actions {
  display: flex;
  gap: 8px;
}

.btn-shortcut {
  padding: 4px 8px;
  background: rgba(0, 198, 255, 0.08);
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-shortcut:hover {
  background: rgba(0, 198, 255, 0.15);
  border-color: var(--border-secondary);
}

/* 快捷指令面板 */
.shortcuts-panel {
  position: absolute;
  bottom: 100%;
  left: 24px;
  right: 24px;
  background: rgba(10, 14, 26, 0.95);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.4);
  padding: 8px;
  margin-bottom: 8px;
  animation: fadeInScale 0.2s ease;
}

@keyframes fadeInScale {
  from { opacity: 0; transform: scale(0.95) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.shortcut-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.shortcut-item:hover {
  background: rgba(0, 198, 255, 0.08);
  border-color: var(--border-primary);
}

.shortcut-command {
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 13px;
  color: var(--accent-cyan);
  font-weight: 600;
}

.shortcut-desc {
  font-size: 12px;
  color: var(--text-muted);
}

/* 错误提示 */
.error-toast {
  position: fixed;
  top: 20px;
  right: 20px;
  background: rgba(239, 68, 68, 0.9);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: white;
  padding: 14px 18px;
  border-radius: 10px;
  border: 1px solid rgba(239, 68, 68, 0.5);
  box-shadow: 0 8px 24px rgba(239, 68, 68, 0.3);
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 1000;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.error-icon {
  font-size: 18px;
}

.error-text {
  flex: 1;
  font-size: 14px;
}

.btn-close-error {
  background: none;
  border: none;
  color: white;
  font-size: 20px;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.3s;
}

.btn-close-error:hover {
  opacity: 0.7;
}

/* 滚动条样式 */
.chat-messages::-webkit-scrollbar,
.history-list::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track,
.history-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
}

.chat-messages::-webkit-scrollbar-thumb,
.history-list::-webkit-scrollbar-thumb {
  background: rgba(0, 198, 255, 0.3);
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover,
.history-list::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 198, 255, 0.5);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chat-container {
    height: calc(100vh - 60px);
  }

  .chat-header {
    padding: 12px 16px;
  }

  .chat-header h2 {
    font-size: 18px;
  }

  .chat-messages {
    padding: 16px;
  }

  .message-content {
    max-width: 85%;
  }

  .chat-input-area {
    padding: 12px 16px;
  }

  .input-wrapper {
    flex-direction: column;
  }

  .btn-send {
    width: 100%;
  }

  .action-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .history-sidebar {
    width: 100%;
  }
}
</style>
