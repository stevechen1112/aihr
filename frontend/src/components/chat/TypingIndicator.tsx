interface Props {
  status?: string
}

/**
 * T7-14: 打字指示器
 * 在 AI 回答時顯示動態波浪效果及狀態文字
 */
export default function TypingIndicator({ status }: Props) {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="rounded-2xl bg-white border border-gray-200 px-4 py-3 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
          {status && (
            <span className="text-xs text-gray-400">{status}</span>
          )}
        </div>
      </div>
    </div>
  )
}
