# Phase 7：使用者體驗與智能化升級提案

> 撰寫日期：2026-02-09
> 背景：Phase 6 完成 AI 引擎升級（LlamaParse + jieba + HyDE + LLM 生成 + Chunk 去重）後，系統在資料處理與 RAG 檢索已達高水準。本提案聚焦**使用者互動體驗**面向的全面強化。

---

## 目錄

- [現況差距分析](#現況差距分析)
- [升級總覽](#升級總覽)
- [P0：Streaming SSE 逐字輸出](#p0streaming-sse-逐字輸出)
- [P0：Multi-turn Context 多輪對話記憶](#p0multi-turn-context-多輪對話記憶)
- [P1：Chat UX 全面升級](#p1chat-ux-全面升級)
- [P2：Mobile Responsive](#p2mobile-responsive)
- [P2：對話匯出 + 進階分析](#p2對話匯出--進階分析)
- [投入回報分析](#投入回報分析)
- [技術參考資源](#技術參考資源)
- [實作排程建議](#實作排程建議)

---

## 現況差距分析

### 已完成的優勢

| 維度 | 目前能力 |
|------|----------|
| 文件解析 | 23 種格式，LlamaParse 優先 + 原生降級 |
| 檢索引擎 | Semantic + BM25（jieba）+ RRF + Voyage Rerank-2 |
| 查詢擴展 | HyDE 假設性文件（語意/混合模式） |
| LLM 生成 | GPT-4o-mini，嚴格引用限制 + fallback 模板 |
| Chunk 去重 | Per-document SHA256 雜湊 |
| 多租戶隔離 | DB/Vector/File/API/Cache 五層隔離 |
| 安全機制 | JWT + SSO + 三層速率限制 + IP 白名單 |
| 監控 | Prometheus + Grafana + 告警規則 |

### 待改進的痛點

| 維度 | 現況 | 問題描述 | 影響程度 |
|------|------|----------|----------|
| **Chat 回應方式** | 一次回傳完整 JSON | 使用者等 5-15 秒只看到 spinner 轉圈 | 🔴 嚴重 |
| **多輪對話** | 每次查詢獨立，不帶歷史 | 追問「那加班費呢？」失去上下文 | 🔴 嚴重 |
| **回覆呈現** | `whitespace-pre-wrap` 純文字 | 表格、列表、粗體無法正確渲染 | 🟠 中等 |
| **來源引用** | 靜態 badge 標籤 | 無法點開查看具體引用段落與法條 | 🟠 中等 |
| **使用者回饋** | 完全沒有 feedback 機制 | 無法量化回答品質、無法迭代改善 | 🟠 中等 |
| **行動裝置** | 側邊欄固定 256px | 手機螢幕無法使用 | 🟡 一般 |
| **對話匯出** | 無 | 企業合規場景需要 | 🟡 一般 |
| **追問引導** | 無 | 使用者不知道可以問什麼 | 🟡 一般 |

---

## 升級總覽

```
Phase 7 升級項目（4 大項，11 子任務）

┌─────────────────────────────────────────────────────────┐
│                     P0 核心體驗                          │
│  ┌─────────────────────┐ ┌─────────────────────────────┐│
│  │  T7-1 Streaming SSE │ │ T7-2 Multi-turn Context     ││
│  │  後端 SSE 串流       │ │ 歷史注入 + Token 管理        ││
│  │  前端逐字渲染        │ │ 滑動窗口 + 摘要壓縮          ││
│  └─────────────────────┘ └─────────────────────────────┘│
├─────────────────────────────────────────────────────────┤
│                     P1 體驗強化                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ T7-3 Markdown│ │ T7-4 Source  │ │ T7-5 Feedback    │ │
│  │ 渲染引擎     │ │ 引用展開     │ │ 👍👎 系統        │ │
│  └──────────────┘ └──────────────┘ └──────────────────┘ │
│  ┌──────────────┐                                       │
│  │ T7-6 Follow  │                                       │
│  │ -up 建議     │                                       │
│  └──────────────┘                                       │
├─────────────────────────────────────────────────────────┤
│                     P2 擴展功能                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ T7-9 Mobile  │ │ T7-11 Chat   │ │ T7-12 RAG       │ │
│  │ Responsive   │ │ Export       │ │ 品質儀表板       │ │
│  ├──────────────┤ ├──────────────┤ ├──────────────────┤ │
│  │ T7-13 Chat   │ │ T7-14 Typing │ │                  │ │
│  │ 搜尋         │ │ Indicator    │ │                  │ │
│  └──────────────┘ └──────────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## P0：Streaming SSE 逐字輸出

### 問題

目前 `POST /api/v1/chat` 回傳完整 JSON，使用者送出問題後：
1. 前端顯示 `<Loader2 className="animate-spin" />` + 「思考中...」
2. 等待 5-15 秒（含檢索 + Rerank + LLM 生成）
3. 完整回答一次出現

**這是 SaaS AI 產品最大的體驗瓶頸** — 競品如 ChatGPT、Claude、Perplexity 全部採用串流輸出。

### 方案

#### T7-1：後端 SSE 串流 + 前端逐字渲染

**後端改動**（`chat_orchestrator.py` + `chat.py`）：

> 前置重構（T7-0）：現有 `process_query` 綁定了檢索與生成。需拆分為 `retrieve_context`（並行查詢內規+勞動法）與 `generate_answer`（純生成），以便在串流端點中分階段呼叫。

```python
# app/api/v1/endpoints/chat.py — 新增串流端點
from fastapi.responses import StreamingResponse

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, ...):
    orchestrator = ChatOrchestrator()
    
    async def event_generator():
        # Phase 1: 快速回饋 — 告知使用者「正在檢索」
        yield f"data: {json.dumps({'type': 'status', 'content': '正在搜尋知識庫...'})}\n\n"
        
        # Phase 2: 檢索（分離出的檢索邏輯）
        # retrieve_context 需包含：KB search + Core API call
        context_results = await orchestrator.retrieve_context(
            tenant_id=current_user.tenant_id, 
            question=request.question
        )
        
        # 立即回傳來源資料
        yield f"data: {json.dumps({'type': 'sources', 'sources': context_results['sources']})}\n\n"
        
        # Phase 3: LLM 串流生成
        yield f"data: {json.dumps({'type': 'status', 'content': '正在生成回答...'})}\n\n"
        
        async for chunk in orchestrator.stream_answer(
            question=request.question, 
            context_results=context_results
        ):
            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
        
        # Phase 4: 完成
        yield f"data: {json.dumps({'type': 'done', 'message_id': ...})}\n\n"
    
    headers = {
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      # 若走 Nginx/反向代理，常需要關閉 buffering 才能即時串流
      # "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)
```

```python
# app/services/chat_orchestrator.py — 重構與新增
class ChatOrchestrator:
    async def retrieve_context(self, tenant_id: UUID, question: str) -> Dict[str, Any]:
        """(T7-0) 從 process_query 拆分出的純檢索邏輯"""
        # 並行執行：
        # 1. self.kb_retriever.search(...)
        # 2. self.core_client.chat(...)
        # 3. 合併結果並回傳 (類似原 _merge_results 但不含生成)
        ...

    async def stream_answer(self, question: str, context_results: Dict[str, Any]):
        """(T7-1) 串流生成 LLM 回答"""
        # 組裝 Prompt (使用 context_results)
        messages = self._build_prompt(question, context_results)
        
        response = await self.openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            stream=True  # ← 關鍵
        )
        
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

**前端改動**（`ChatPage.tsx`）：

```tsx
// 使用 fetch + ReadableStream 接收串流（解析 text/event-stream）
const sendStreamMessage = async (content: string) => {
  // 立即顯示使用者訊息
  setMessages(prev => [...prev, { role: 'user', content }]);
  
  // 建立串流連線
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ message: content, conversation_id: convId }),
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let assistantMsg = '';
  
  // 先加入空的 assistant 訊息
  setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }]);
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const lines = decoder.decode(value).split('\n');
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const data = JSON.parse(line.slice(6));
      
      if (data.type === 'token') {
        assistantMsg += data.content;
        // 更新最後一條 assistant 訊息（逐字增長）
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { ...updated[updated.length - 1], content: assistantMsg };
          return updated;
        });
      } else if (data.type === 'sources') {
        setSources(data.sources);
      }
    }
  }
};
```

**效果**：

| 指標 | Before | After |
|------|--------|-------|
| 首字出現時間 | 5-15 秒 | < 1 秒 |
| 感知延遲 | 高（空白等待） | 低（逐字出現） |
| 使用者體驗 | 焦慮 | 自然對話感 |

---

## P0：Multi-turn Context 多輪對話記憶

### 問題

目前 `process_query()` 每次查詢完全獨立：

```python
# 現狀 — chat_orchestrator.py
async def process_query(self, query: str, tenant_id: str, ...):
    # ← 沒有 conversation history 參數
    results = await self._retrieve(query, tenant_id)
    answer = await self._generate_answer(query, results)
    return answer
```

使用者對話場景：
```
User: 公司特休假有幾天？
AI:   依年資計算，滿1年7天，滿2年10天...（正確回答）

User: 那未休完的怎麼算？   ← 「那」= 特休假，但系統不知道
AI:   請問您想了解什麼主題？  ← 失去上下文
```

### 方案

#### T7-2：歷史注入 + 滑動窗口 + Token 管理

> 備註：查詢改寫會帶來額外成本與延遲，建議「有需要才啟用」：例如新問題包含代名詞（那/它/這個/上述）或明顯省略主詞時才進行 `_contextualize_query()`，否則直接用原 query。

```python
# app/services/chat_orchestrator.py

async def process_query(
    self, query: str, tenant_id: str, 
    conversation_id: str = None,  # 新增
    max_history_turns: int = 5,   # 新增：最多帶入最近 N 輪
):
    # 1. 取得歷史對話
    history = []
    if conversation_id:
        history = await self._get_conversation_history(
            conversation_id, max_turns=max_history_turns
        )
    
    # 2. 用歷史改寫查詢（解決代名詞問題）
    contextualized_query = await self._contextualize_query(query, history)
    
    # 3. 用改寫後的查詢做檢索
    results = await self._retrieve(contextualized_query, tenant_id)
    
    # 4. 帶入歷史 + 檢索結果生成回答
    answer = await self._generate_answer(query, results, history)
    return answer

async def _contextualize_query(self, query: str, history: list) -> str:
    """用 LLM 將模糊查詢改寫為獨立查詢"""
    if not history:
        return query
    
    # 輕量 prompt：只做查詢改寫，不做回答
    messages = [
        {"role": "system", "content": (
            "根據對話歷史，將使用者的最新問題改寫為一個獨立、完整的查詢。"
            "只輸出改寫後的查詢，不要解釋。如果問題已經夠明確，直接原樣輸出。"
        )},
        *[{"role": m["role"], "content": m["content"]} for m in history[-4:]],
        {"role": "user", "content": query}
    ]
    
    response = await self.openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0,
        max_tokens=200
    )
    return response.choices[0].message.content.strip()

def _build_messages_with_history(self, query, context, history):
    """組裝帶歷史的 LLM messages"""
    messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
    
    # Token 預算管理
    total_tokens = 0
    max_history_tokens = 2000  # 歷史最多佔 2000 tokens
    
    # 建議：使用 tiktoken/實際 tokenizer 估算 tokens（Phase 6 既有 TextChunker 已使用 tokenizer）
    for msg in reversed(history):
      msg_tokens = len(msg["content"]) // 2  # 粗估（提案用，實作時請改為 tokenizer）
        if total_tokens + msg_tokens > max_history_tokens:
            break
        messages.insert(1, {"role": msg["role"], "content": msg["content"]})
        total_tokens += msg_tokens
    
    # 加入檢索上下文
    messages.append({"role": "user", "content": self._format_context(query, context)})
    return messages
```

**效果範例**：

```
User: 公司特休假有幾天？
AI:   依年資計算，滿1年7天，滿2年10天...

User: 那未休完的怎麼算？
      ↓ 改寫為: 「特休假未休完的天數如何計算補償？」
AI:   依勞基法第38條第4項，年度終結或契約終止時，
      未休之特休假日數，雇主應折發工資...  ✅ 正確回答
```

---

## P1：Chat UX 全面升級

### T7-3：Markdown 渲染引擎

**問題**：LLM 回覆含 Markdown 語法（`**粗體**`、`| 表格 |`、`- 列表`），但前端以純文字顯示。

**方案**：

```bash
# 前端依賴
cd frontend && npm install react-markdown remark-gfm rehype-highlight
```

```tsx
// frontend/src/components/MarkdownRenderer.tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function MarkdownRenderer({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="min-w-full border-collapse border border-gray-300 text-sm">
              {children}
            </table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border border-gray-300 bg-gray-100 px-3 py-1.5 text-left font-medium">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-gray-300 px-3 py-1.5">{children}</td>
        ),
        ul: ({ children }) => <ul className="list-disc pl-5 my-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-5 my-1">{children}</ol>,
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener" className="text-blue-600 underline">
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
```

### T7-4：來源引用展開

**現況**：assistant 訊息底部有 `公司內規`、`勞動法規` 靜態 badge，無法點擊。

**方案**：

```tsx
// frontend/src/components/SourcePanel.tsx
function SourcePanel({ sources }: { sources: Source[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className="mt-3 border-t pt-2">
      <p className="text-xs text-gray-500 mb-1">📎 參考來源（{sources.length}）</p>
      {sources.map((src, i) => (
        <div key={i} className="mb-1">
          <button
            onClick={() => setExpanded(expanded === i ? null : i)}
            className="flex items-center gap-2 text-sm text-left w-full hover:bg-gray-50 rounded px-2 py-1"
          >
            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
              src.type === 'company_policy' 
                ? 'bg-blue-100 text-blue-700' 
                : 'bg-green-100 text-green-700'
            }`}>
              {src.type === 'company_policy' ? '公司內規' : '勞動法規'}
            </span>
            <span className="flex-1 truncate">{src.filename || src.title}</span>
            <span className="text-xs text-gray-400">
              {(src.score * 100).toFixed(0)}% 相關
            </span>
            <ChevronDown className={`w-4 h-4 transition-transform ${expanded === i ? 'rotate-180' : ''}`} />
          </button>
          
          {expanded === i && (
            <div className="ml-4 mt-1 p-2 bg-gray-50 rounded text-sm text-gray-700 border-l-2 border-blue-300">
              <p className="whitespace-pre-wrap">{src.content}</p>
              {src.metadata?.page && (
                <p className="text-xs text-gray-400 mt-1">第 {src.metadata.page} 頁</p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

> 備註：實作時請優先沿用既有 `BrandingContext`/既有 Tailwind token（避免新增硬編碼色彩與樣式）。上述僅為互動結構示例。

### T7-5：Feedback 回饋系統

**資料模型**：

```python
# app/models/feedback.py
class ChatFeedback(Base):
    __tablename__ = "chat_feedback"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False, index=True)
    message_id = Column(UUID, ForeignKey("messages.id"), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    rating = Column(SmallInteger, nullable=False)  # 1=👎, 2=👍
    category = Column(String(50))  # wrong_answer / incomplete / outdated / other
    comment = Column(Text)
    created_at = Column(DateTime, default=func.now())

    # 建議：同一使用者對同一則訊息僅允許 1 筆回饋（可更新），避免灌票
    __table_args__ = (UniqueConstraint("user_id", "message_id", name="uq_feedback_user_message"),)
```

**API 端點**：

```python
# app/api/v1/endpoints/feedback.py
@router.post("/feedback")
async def submit_feedback(feedback: FeedbackCreate, current_user = Depends(get_current_user)):
    ...

@router.get("/feedback/stats")
async def feedback_stats(current_user = Depends(require_admin)):
    # 返回：好評率、差評原因分佈、趨勢圖數據
    ...
```

**前端 UI**：

```tsx
// 在每條 assistant 訊息底部
<div className="flex items-center gap-2 mt-2">
  <button onClick={() => submitFeedback(msg.id, 2)} 
    className="p-1 rounded hover:bg-green-50">
    <ThumbsUp className="w-4 h-4 text-gray-400 hover:text-green-600" />
  </button>
  <button onClick={() => submitFeedback(msg.id, 1)}
    className="p-1 rounded hover:bg-red-50">
    <ThumbsDown className="w-4 h-4 text-gray-400 hover:text-red-600" />
  </button>
</div>
```

### T7-6：Follow-up 建議問題

**後端**：在 LLM 生成回答後，額外生成 2-3 個追問建議。

> 建議：不要把「建議問題」直接拼進 answer 文字（容易污染引用/Markdown/匯出）。較穩健做法是回傳 `suggested_questions: string[]` 作為獨立欄位（SSE 亦可用 `type: 'suggestions'` 事件傳送）。

```python
# 在 system prompt 末尾加入
FOLLOWUP_PROMPT = """
在回答的最後，請另起一行輸出 3 個建議的追問問題，格式：
[建議問題]
1. ...
2. ...
3. ...
"""
```

**前端**：解析 `[建議問題]` 區塊，渲染為可點擊的按鈕。

```tsx
// 解析建議問題
const suggestions = parseSuggestions(msg.content);

{suggestions.length > 0 && (
  <div className="flex flex-wrap gap-2 mt-3">
    {suggestions.map((q, i) => (
      <button key={i} onClick={() => sendMessage(q)}
        className="text-sm px-3 py-1.5 rounded-full border border-blue-200 
                   text-blue-700 hover:bg-blue-50 transition">
        {q}
      </button>
    ))}
  </div>
)}
```

---

## P2：Mobile Responsive

### T7-9：行動裝置適配

**現況問題**：
- 側邊欄 `w-64`（256px）固定寬度，手機上佔滿螢幕
- 無漢堡選單按鈕
- 輸入區域在小螢幕上太窄

**方案**：

```tsx
// frontend/src/components/Layout.tsx — 響應式側邊欄
function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  return (
    <div className="flex h-screen">
      {/* Overlay（行動版） */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 md:hidden" 
             onClick={() => setSidebarOpen(false)} />
      )}
      
      {/* 側邊欄 */}
      <aside className={`
        fixed md:static inset-y-0 left-0 z-50
        w-64 bg-white border-r transform transition-transform
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        md:translate-x-0
      `}>
        ...
      </aside>
      
      {/* 主內容 */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* 行動版 Header + 漢堡選單 */}
        <header className="md:hidden flex items-center gap-3 p-3 border-b">
          <button onClick={() => setSidebarOpen(true)}>
            <Menu className="w-6 h-6" />
          </button>
          <h1 className="font-semibold">UniHR AI</h1>
        </header>
        ...
      </main>
    </div>
  );
}
```

---

## P2：對話匯出 + 進階分析

### T7-11：對話匯出

```python
# app/api/v1/endpoints/chat.py
@router.get("/chat/conversations/{id}/export")
async def export_conversation(
    id: UUID, 
    format: str = Query("markdown", enum=["markdown", "pdf"]),
    current_user = Depends(get_current_user)
):
    messages = await get_conversation_messages(id, current_user.tenant_id)
    
    if format == "markdown":
        content = render_markdown_export(messages)
        return Response(content, media_type="text/markdown",
                       headers={"Content-Disposition": f"attachment; filename=conversation_{id}.md"})
    elif format == "pdf":
        pdf_bytes = render_pdf_export(messages)
        return Response(pdf_bytes, media_type="application/pdf",
                       headers={"Content-Disposition": f"attachment; filename=conversation_{id}.pdf"})
```

### T7-12：RAG 品質儀表板

新增 Analytics 面板，追蹤：

| 指標 | 數據來源 | 呈現方式 |
|------|----------|----------|
| 好評率 | `chat_feedback` | 折線圖趨勢 |
| 差評原因分佈 | `chat_feedback.category` | 圓餅圖 |
| 平均回應時間 | `retrieval_trace.latency_ms` | 折線圖 |
| 熱門問題 Top 10 | `messages` 聚類 | 橫條圖 |
| 無結果查詢率 | `retrieval_trace.sources_json` 為空 | 單一指標 |
| 來源引用分佈 | `company_policy` vs `labor_law` | 堆疊柱狀圖 |

### T7-13：對話搜尋

```tsx
// 前端 — 對話列表上方加搜尋框
<input 
  type="search" 
  placeholder="搜尋對話..."
  value={searchQuery}
  onChange={(e) => setSearchQuery(e.target.value)}
  className="w-full px-3 py-1.5 text-sm border rounded"
/>
```

```python
# 後端 — 全文搜尋對話
@router.get("/chat/conversations/search")
async def search_conversations(q: str, current_user = Depends(get_current_user)):
    results = await db.execute(
        select(Message).join(Conversation)
        .where(Conversation.tenant_id == current_user.tenant_id)
        .where(Message.content.ilike(f"%{q}%"))
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    return results.scalars().all()
```

  > 備註：`ILIKE '%...%'` 在資料量大時效能會快速下降。若要進一步產品化，建議改用 PostgreSQL Full-Text Search（`tsvector`）或 trigram index（`pg_trgm`）。

### T7-14：Typing Indicator

在等待 AI 回覆時顯示打字指示器動畫：

```tsx
// frontend/src/components/TypingIndicator.tsx
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-2">
      <div className="flex gap-1">
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
      </div>
      <span className="text-sm text-gray-400 ml-2">AI 正在輸入...</span>
    </div>
  );
}
```

---

## 投入回報分析

### 投入 vs 影響力矩陣

```
影響力 ↑
  高  │ ★ Streaming SSE    ★ Multi-turn Context
      │   Feedback System     Markdown Render
      │   Source Expand        Guardrails
  中  │   Follow-up Q's       Dark Mode
      │   Chat Export          Mobile Responsive
      │   RAG Dashboard
  低  │   Typing Indicator    Chat Search
      │
      └──────────────────────────────────────→ 實作複雜度
           簡單（1-2天）      中等（3-5天）     複雜（1週+）
```

### 各項目預估工時

| ID | 項目 | 後端工時 | 前端工時 | 總計 | 優先級 |
|----|------|----------|----------|------|--------|
| T7-1 | Streaming SSE | 4h | 4h | **1 天** | 🔴 P0 |
| T7-2 | Multi-turn Context | 6h | 2h | **1 天** | 🔴 P0 |
| T7-3 | Markdown 渲染 | 0 | 3h | **0.5 天** | 🟠 P1 |
| T7-4 | Source 展開 | 2h | 4h | **1 天** | 🟠 P1 |
| T7-5 | Feedback 系統 | 4h | 4h | **1 天** | 🟠 P1 |
| T7-6 | Follow-up 建議 | 2h | 3h | **0.5 天** | 🟠 P1 |
| T7-9 | Mobile Responsive | 0 | 6h | **1 天** | 🟡 P2 |
| T7-11 | Chat Export | 4h | 2h | **1 天** | 🟡 P2 |
| T7-12 | RAG 品質儀表板 | 4h | 6h | **1.5 天** | 🟡 P2 |
| T7-13 | Chat Search | 2h | 2h | **0.5 天** | 🟡 P2 |
| T7-14 | Typing Indicator | 0 | 1h | **0.5 天** | 🟡 P2 |
| | | | **合計** | **~9 天** | |

### 預估新增依賴

| 套件 | 用途 | 層級 |
|------|------|------|
| `sse-starlette` | FastAPI SSE 支援 | 後端 |
| `react-markdown` | Markdown 渲染 | 前端 |
| `remark-gfm` | GFM 表格/刪除線 | 前端 |
| `rehype-highlight` | 程式碼高亮 | 前端（選配） |

---

## 技術參考資源

| 參考 | 類型 | 用途 |
|------|------|------|
| [OpenAI Streaming Guide](https://platform.openai.com/docs/api-reference/chat/create#chat-create-stream) | 官方文件 | T7-1 SSE 串流 |
| [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse) | 官方文件 | T7-1 後端串流 |
| [ChatGPT](https://chat.openai.com) | 產品參考 | T7-1 串流 UX / T7-6 Follow-up |
| [Perplexity](https://perplexity.ai) | 產品參考 | T7-4 來源引用展開 |
| [Claude](https://claude.ai) | 產品參考 | T7-3 Markdown 渲染 |
| [RAGAS](https://github.com/explodinggradients/ragas) | 開源框架 | T7-12 RAG 品質評估 |
| [react-markdown](https://github.com/remarkjs/react-markdown) | 開源套件 | T7-3 前端 Markdown |
| [AnythingLLM](https://github.com/Mintplex-Labs/anything-llm) | 產品參考 | T7-5 Feedback UI |

---

## 實作排程建議

```
Week 1（P0 核心體驗）
├── Day 1-2: T7-1 Streaming SSE（後端 + 前端）
├── Day 3-4: T7-2 Multi-turn Context（查詢改寫 + 歷史注入）
└── Day 5:   T7-3 Markdown 渲染 + T7-14 Typing Indicator

Week 2（P1 體驗強化）
├── Day 1:   T7-4 Source 引用展開
├── Day 2:   T7-5 Feedback 系統（Model + API + UI）
├── Day 3:   T7-6 Follow-up 建議
└── Day 4-5: 整合測試 + Bug 修復

Week 3（P2 擴展功能）
├── Day 1:   T7-9 Mobile Responsive
├── Day 2:   T7-11 Chat Export + T7-13 Chat Search
├── Day 3-4: T7-12 RAG 品質儀表板
└── Day 5:   全面測試 + README 更新 + 部署

總計：3 週（13 個工作天 預留緩衝）
```

---

## 變更影響範圍

### 後端檔案

| 檔案 | 變更類型 | 相關任務 |
|------|----------|----------|
| `app/services/chat_orchestrator.py` | 重構 | T7-1, T7-2, T7-6 |
| `app/api/v1/endpoints/chat.py` | 新增端點 | T7-1, T7-11, T7-13 |
| `app/models/feedback.py` | 新增 | T7-5 |
| `app/schemas/feedback.py` | 新增 | T7-5 |
| `app/api/v1/endpoints/feedback.py` | 新增 | T7-5, T7-12 |
| `requirements.txt` | 更新 | T7-1 |
| `alembic/versions/xxx_add_feedback.py` | 新增 | T7-5 |

### 前端檔案

| 檔案 | 變更類型 | 相關任務 |
|------|----------|----------|
| `frontend/src/pages/ChatPage.tsx` | 重構 | T7-1, T7-2, T7-14 |
| `frontend/src/components/MarkdownRenderer.tsx` | 新增 | T7-3 |
| `frontend/src/components/SourcePanel.tsx` | 新增 | T7-4 |
| `frontend/src/components/FeedbackButtons.tsx` | 新增 | T7-5 |
| `frontend/src/components/FollowUpSuggestions.tsx` | 新增 | T7-6 |
| `frontend/src/components/TypingIndicator.tsx` | 新增 | T7-14 |
| `frontend/src/components/Layout.tsx` | 修改 | T7-9 |
| `frontend/package.json` | 更新 | T7-3 |

---

## 成功指標

| 指標 | 目前基線 | Phase 7 目標 |
|------|----------|-------------|
| 首字回應時間 | 5-15 秒 | < 1 秒 |
| 多輪對話成功率 | 0%（不支援） | > 85% |
| 使用者回饋收集率 | 0%（無機制） | > 30% 訊息有回饋 |
| Markdown 正確渲染率 | 0% | 100% |
| 行動裝置可用性 | 不可用 | 完整可用 |

---

> 本提案基於 Phase 6 完成後的完整程式碼審查，參考 ChatGPT、Claude、Perplexity、AnythingLLM 等產品的最佳實踐，結合企業 HR SaaS 的合規需求而制定。
