import { useState, useEffect, useRef, useCallback } from 'react'
import { chatApi } from '../api'
import { useAuth } from '../auth'
import type { Conversation, Message } from '../types'
import { Send, Plus, Loader2, MessageSquare, Trash2, ClipboardList, Scale } from 'lucide-react'
import clsx from 'clsx'
import { format } from 'date-fns'
import toast from 'react-hot-toast'

export default function ChatPage() {
  const { user } = useAuth()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConvId, setActiveConvId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingConvs, setLoadingConvs] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load conversations
  const loadConversations = useCallback(async () => {
    try {
      const convs = await chatApi.conversations()
      setConversations(convs)
    } catch {
      // ignore
    } finally {
      setLoadingConvs(false)
    }
  }, [])

  useEffect(() => { loadConversations() }, [loadConversations])

  // Load messages when conversation changes
  useEffect(() => {
    if (!activeConvId) {
      setMessages([])
      return
    }
    chatApi.messages(activeConvId).then(setMessages).catch(() => {})
  }, [activeConvId])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const question = input.trim()
    if (!question || sending) return

    // Optimistic UI
    const tempUserMsg: Message = {
      id: 'temp-' + Date.now(),
      conversation_id: activeConvId || '',
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, tempUserMsg])
    setInput('')
    setSending(true)

    try {
      const res = await chatApi.send({
        question,
        conversation_id: activeConvId,
      })

      // If new conversation, update
      if (!activeConvId) {
        setActiveConvId(res.conversation_id)
        loadConversations()
      }

      const assistantMsg: Message = {
        id: res.message_id,
        conversation_id: res.conversation_id,
        role: 'assistant',
        content: res.answer,
        created_at: new Date().toISOString(),
      }
      setMessages(prev => [...prev.filter(m => m.id !== tempUserMsg.id), { ...tempUserMsg, id: 'user-' + Date.now() }, assistantMsg])
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '發送失敗，請稍後重試'
      toast.error(msg)
      setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id))
      setInput(question)
    } finally {
      setSending(false)
    }
  }

  const handleNewChat = () => {
    setActiveConvId(null)
    setMessages([])
    setInput('')
  }

  const handleDeleteConv = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('確定要刪除此對話？')) return
    try {
      await chatApi.deleteConversation(convId)
      if (activeConvId === convId) handleNewChat()
      setConversations(prev => prev.filter(c => c.id !== convId))
      toast.success('對話已刪除')
    } catch {
      toast.error('刪除失敗')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-full">
      {/* Conversation sidebar */}
      <div className="flex w-64 flex-col border-r border-gray-200 bg-white">
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-gray-700">對話記錄</h2>
          <button onClick={handleNewChat} className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 hover:text-blue-600 transition-colors" title="新對話">
            <Plus className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
          {loadingConvs ? (
            <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-gray-400" /></div>
          ) : conversations.length === 0 ? (
            <p className="py-8 text-center text-xs text-gray-400">尚無對話</p>
          ) : (
            conversations.map(conv => (
              <div
                key={conv.id}
                onClick={() => setActiveConvId(conv.id)}
                className={clsx(
                  'group flex items-center justify-between rounded-lg px-3 py-2 text-sm cursor-pointer transition-colors',
                  activeConvId === conv.id ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-50'
                )}
              >
                <div className="flex-1 truncate">
                  <p className="truncate font-medium">{conv.title || '新對話'}</p>
                  <p className="text-xs text-gray-400">{format(new Date(conv.created_at), 'MM/dd HH:mm')}</p>
                </div>
                <button
                  onClick={(e) => handleDeleteConv(conv.id, e)}
                  className="ml-2 hidden rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 group-hover:block transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex flex-1 flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-gray-400">
              <MessageSquare className="mb-4 h-12 w-12" />
              <h3 className="text-lg font-medium text-gray-600">你好，{user?.full_name || '用戶'}！</h3>
              <p className="mt-1 text-sm">有什麼人資相關的問題想問嗎？</p>
              <div className="mt-6 grid grid-cols-2 gap-3">
                {['特休假怎麼算？', '加班費計算方式？', '資遣費的規定？', '勞工保險包含哪些？'].map(q => (
                  <button
                    key={q}
                    onClick={() => setInput(q)}
                    className="rounded-xl border border-gray-200 px-4 py-3 text-left text-sm text-gray-600 hover:border-blue-300 hover:bg-blue-50 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-4">
              {messages.map(msg => (
                <div key={msg.id} className={clsx('animate-fade-in flex', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
                  <div className={clsx(
                    'max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-800 border border-gray-200 shadow-sm'
                  )}>
                    {msg.role === 'assistant' ? (
                      <div className="space-y-2">
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                        {/* Source badges */}
                        <div className="flex gap-2 pt-1 border-t border-gray-100">
                          <span className="inline-flex items-center gap-1 text-xs text-gray-400">
                            <ClipboardList className="h-3 w-3" /> 公司內規
                          </span>
                          <span className="inline-flex items-center gap-1 text-xs text-gray-400">
                            <Scale className="h-3 w-3" /> 勞動法規
                          </span>
                        </div>
                      </div>
                    ) : (
                      <span>{msg.content}</span>
                    )}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start animate-fade-in">
                  <div className="rounded-2xl bg-white border border-gray-200 px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                      <Loader2 className="h-4 w-4 animate-spin" /> 思考中...
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 bg-white p-4">
          <div className="mx-auto flex max-w-3xl items-end gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="輸入你的問題..."
              rows={1}
              className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-shadow"
              style={{ maxHeight: '120px' }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement
                target.style.height = 'auto'
                target.style.height = Math.min(target.scrollHeight, 120) + 'px'
              }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 transition-colors shrink-0"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
