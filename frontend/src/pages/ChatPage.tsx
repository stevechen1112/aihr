import { useState, useEffect, useRef, useCallback } from 'react'
import { chatApi } from '../api'
import { useAuth } from '../auth'
import type { Conversation, Message, ChatSource, SSEEvent, SearchResult } from '../types'
import {
  Send, Plus, Loader2, MessageSquare, Trash2,
  Download, Search, X,
} from 'lucide-react'
import clsx from 'clsx'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import MarkdownRenderer from '../components/chat/MarkdownRenderer'
import SourcePanel from '../components/chat/SourcePanel'
import FeedbackButtons from '../components/chat/FeedbackButtons'
import FollowUpSuggestions from '../components/chat/FollowUpSuggestions'
import TypingIndicator from '../components/chat/TypingIndicator'

/** 擴展 Message 在前端增加附帶資料 */
interface ChatMessage extends Message {
  sources?: ChatSource[]
  suggestions?: string[]
}

export default function ChatPage() {
  const { user } = useAuth()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConvId, setActiveConvId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingConvs, setLoadingConvs] = useState(true)
  const [streamStatus, setStreamStatus] = useState<string | null>(null)
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingSources, setStreamingSources] = useState<ChatSource[]>([])

  // T7-13: search
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

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

  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  // Load messages when conversation changes
  useEffect(() => {
    if (!activeConvId) {
      setMessages([])
      return
    }
    chatApi.messages(activeConvId).then(msgs => setMessages(msgs)).catch(() => {})
  }, [activeConvId])

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  // ──────── T7-1: SSE Streaming send ────────
  const handleSend = async () => {
    const question = input.trim()
    if (!question || sending) return

    // Optimistic user message
    const tempUserMsg: ChatMessage = {
      id: 'temp-' + Date.now(),
      conversation_id: activeConvId || '',
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, tempUserMsg])
    setInput('')
    setSending(true)
    setStreamingContent('')
    setStreamingSources([])
    setStreamStatus(null)

    const abortController = new AbortController()
    abortRef.current = abortController

    let finalConvId = activeConvId
    let finalMessageId = ''
    let accumulatedContent = ''
    let suggestions: string[] = []
    let sources: ChatSource[] = []
    let hadStreamError = false

    try {
      await chatApi.stream(
        { question, conversation_id: activeConvId },
        (event: SSEEvent) => {
          switch (event.type) {
            case 'status':
              setStreamStatus(event.content || null)
              break
            case 'sources':
              sources = event.sources || []
              setStreamingSources(sources)
              break
            case 'token':
              accumulatedContent += event.content || ''
              setStreamingContent(accumulatedContent)
              setStreamStatus(null) // hide status once tokens flow
              break
            case 'suggestions':
              suggestions = event.items || []
              break
            case 'done':
              finalConvId = event.conversation_id || finalConvId
              finalMessageId = event.message_id || ''
              break
            case 'error':
              hadStreamError = true
              toast.error(event.content || '處理失敗')
              break
          }
        },
        abortController.signal,
      )

      if (hadStreamError) {
        setStreamingContent('')
        setStreamingSources([])
        setStreamStatus(null)
        setInput(question)
        return
      }

      // Stream finished — commit assistant message
      const assistantMsg: ChatMessage = {
        id: finalMessageId || 'ai-' + Date.now(),
        conversation_id: finalConvId || '',
        role: 'assistant',
        content: accumulatedContent,
        created_at: new Date().toISOString(),
        sources,
        suggestions,
      }

      setMessages(prev => [
        ...prev.filter(m => m.id !== tempUserMsg.id),
        { ...tempUserMsg, id: 'user-' + Date.now(), conversation_id: finalConvId || '' },
        assistantMsg,
      ])
      setStreamingContent('')
      setStreamingSources([])
      setStreamStatus(null)

      // Update conversation list if new
      if (!activeConvId && finalConvId) {
        setActiveConvId(finalConvId)
        loadConversations()
      }
    } catch (err: unknown) {
      if ((err as Error)?.name === 'AbortError') return
      const msg = (err as Error)?.message || '發送失敗，請稍後重試'
      toast.error(msg)
      setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id))
      setInput(question)
    } finally {
      setSending(false)
      setStreamStatus(null)
      abortRef.current = null
    }
  }

  const handleNewChat = () => {
    if (abortRef.current) abortRef.current.abort()
    setActiveConvId(null)
    setMessages([])
    setInput('')
    setStreamingContent('')
    setStreamingSources([])
    setStreamStatus(null)
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

  // T7-11: Export
  const handleExport = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const blob = await chatApi.exportConversation(convId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `conversation_${convId}.md`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('對話已匯出')
    } catch {
      toast.error('匯出失敗')
    }
  }

  // T7-13: Search
  const handleSearch = async () => {
    const q = searchQuery.trim()
    if (!q) {
      setSearchResults(null)
      return
    }
    try {
      const results = await chatApi.searchConversations(q)
      setSearchResults(results)
    } catch {
      toast.error('搜尋失敗')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // T7-6: Follow-up suggestion click
  const handleSuggestionClick = (question: string) => {
    setInput(question)
  }

  // 最後一條 assistant message 的 suggestions
  const lastSuggestions =
    !sending && messages.length > 0 && messages[messages.length - 1]?.role === 'assistant'
      ? messages[messages.length - 1].suggestions
      : undefined

  return (
    <div className="flex h-full">
      {/* ──── Conversation sidebar ──── */}
      <div className="hidden md:flex w-64 flex-col border-r border-gray-200 bg-white">
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-gray-700">對話記錄</h2>
          <button
            onClick={handleNewChat}
            className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 hover:text-[#d15454] transition-colors"
            title="新對話"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>

        {/* T7-13: search bar */}
        <div className="px-3 py-2 border-b border-gray-100">
          <div className="flex items-center gap-1">
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder="搜尋對話..."
              className="flex-1 rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs focus:border-[#d15454] focus:outline-none"
            />
            {searchQuery ? (
              <button
                onClick={() => { setSearchQuery(''); setSearchResults(null) }}
                className="p-1 text-gray-400 hover:text-gray-600"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            ) : (
              <button onClick={handleSearch} className="p-1 text-gray-400 hover:text-gray-600">
                <Search className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Search results or conversation list */}
        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
          {searchResults !== null ? (
            searchResults.length === 0 ? (
              <p className="py-8 text-center text-xs text-gray-400">無搜尋結果</p>
            ) : (
              searchResults.map((r, i) => (
                <div
                  key={i}
                  onClick={() => {
                    setActiveConvId(r.conversation_id)
                    setSearchResults(null)
                    setSearchQuery('')
                  }}
                  className="rounded-lg px-3 py-2 text-xs cursor-pointer hover:bg-gray-50 text-gray-600"
                >
                  <p className="font-medium truncate">{r.conversation_title || '對話'}</p>
                  <p className="text-gray-400 truncate mt-0.5">{r.snippet}</p>
                </div>
              ))
            )
          ) : loadingConvs ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
            </div>
          ) : conversations.length === 0 ? (
            <p className="py-8 text-center text-xs text-gray-400">尚無對話</p>
          ) : (
            conversations.map(conv => (
              <div
                key={conv.id}
                onClick={() => setActiveConvId(conv.id)}
                className={clsx(
                  'group flex items-center justify-between rounded-lg px-3 py-2 text-sm cursor-pointer transition-colors',
                  activeConvId === conv.id ? 'bg-[#d15454]/10 text-[#d15454]' : 'text-gray-600 hover:bg-gray-50',
                )}
              >
                <div className="flex-1 truncate">
                  <p className="truncate font-medium">{conv.title || '新對話'}</p>
                  <p className="text-xs text-gray-400">{format(new Date(conv.created_at), 'MM/dd HH:mm')}</p>
                </div>
                <div className="ml-2 hidden gap-0.5 group-hover:flex">
                  <button
                    onClick={e => handleExport(conv.id, e)}
                    className="rounded p-1 text-gray-400 hover:bg-[#d15454]/10 hover:text-[#d15454] transition-colors"
                    title="匯出"
                  >
                    <Download className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={e => handleDeleteConv(conv.id, e)}
                    className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500 transition-colors"
                    title="刪除"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ──── Chat area ──── */}
      <div className="flex flex-1 flex-col">
        {/* Mobile header */}
        <div className="flex md:hidden items-center justify-between border-b border-gray-200 bg-white px-4 py-2">
          <h2 className="text-sm font-semibold text-gray-700">AI 問答</h2>
          <button
            onClick={handleNewChat}
            className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 hover:text-[#d15454]"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 md:px-6 py-4">
          {messages.length === 0 && !streamingContent ? (
            <div className="flex h-full flex-col items-center justify-center text-gray-400">
              <MessageSquare className="mb-4 h-12 w-12" />
              <h3 className="text-lg font-medium text-gray-600">你好，{user?.full_name || '用戶'}！</h3>
              <p className="mt-1 text-sm">有什麼人資相關的問題想問嗎？</p>
              <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md">
                {['特休假怎麼算？', '加班費計算方式？', '資遣費的規定？', '勞工保險包含哪些？'].map(q => (
                  <button
                    key={q}
                    onClick={() => setInput(q)}
                    className="rounded-xl border border-gray-200 px-4 py-3 text-left text-sm text-gray-600 hover:border-[#d15454]/30 hover:bg-[#d15454]/5 transition-colors"
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
                  <div
                    className={clsx(
                      'max-w-[85%] md:max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
                      msg.role === 'user'
                        ? 'bg-[#d15454] text-white'
                        : 'bg-white text-gray-800 border border-gray-200 shadow-sm',
                    )}
                  >
                    {msg.role === 'assistant' ? (
                      <div>
                        {/* T7-3: Markdown rendering */}
                        <MarkdownRenderer content={msg.content} />
                        {/* T7-4: Source panel */}
                        {msg.sources && msg.sources.length > 0 && <SourcePanel sources={msg.sources} />}
                        {/* T7-5: Feedback */}
                        <FeedbackButtons messageId={msg.id} />
                      </div>
                    ) : (
                      <span>{msg.content}</span>
                    )}
                  </div>
                </div>
              ))}

              {/* ──── Streaming in-progress ──── */}
              {sending && streamingContent && (
                <div className="flex justify-start animate-fade-in">
                  <div className="max-w-[85%] md:max-w-[80%] rounded-2xl bg-white border border-gray-200 px-4 py-3 shadow-sm text-sm leading-relaxed text-gray-800">
                    <MarkdownRenderer content={streamingContent} />
                    {streamingSources.length > 0 && <SourcePanel sources={streamingSources} />}
                  </div>
                </div>
              )}

              {/* T7-14: Typing indicator (before first token arrives) */}
              {sending && !streamingContent && (
                <TypingIndicator status={streamStatus || '思考中...'} />
              )}

              {/* T7-6: Follow-up suggestions (after stream completes) */}
              {lastSuggestions && lastSuggestions.length > 0 && (
                <FollowUpSuggestions suggestions={lastSuggestions} onSelect={handleSuggestionClick} />
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 bg-white p-3 md:p-4">
          <div className="mx-auto flex max-w-3xl items-end gap-2 md:gap-3">
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="輸入你的問題..."
              rows={1}
              className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-[#d15454] focus:ring-2 focus:ring-[#d15454]/20 focus:outline-none transition-shadow"
              style={{ maxHeight: '120px' }}
              onInput={e => {
                const target = e.target as HTMLTextAreaElement
                target.style.height = 'auto'
                target.style.height = Math.min(target.scrollHeight, 120) + 'px'
              }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#d15454] text-white hover:bg-[#c04444] disabled:opacity-40 transition-colors shrink-0"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
