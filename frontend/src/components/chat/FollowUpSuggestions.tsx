import { Lightbulb } from 'lucide-react'

interface Props {
  suggestions: string[]
  onSelect: (question: string) => void
}

/**
 * T7-6: 跟進建議問題
 * 顯示 AI 推薦的後續問題，點擊自動帶入輸入
 */
export default function FollowUpSuggestions({ suggestions, onSelect }: Props) {
  if (!suggestions || suggestions.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2 mt-3 animate-fade-in">
      <span className="flex items-center gap-1 text-xs text-gray-400 mr-1">
        <Lightbulb className="h-3 w-3" /> 你可能想問：
      </span>
      {suggestions.map((s, i) => (
        <button
          key={i}
          onClick={() => onSelect(s)}
          className="rounded-full border border-blue-200 bg-blue-50/60 px-3 py-1 text-xs text-blue-700 hover:bg-blue-100 hover:border-blue-300 transition-colors"
        >
          {s}
        </button>
      ))}
    </div>
  )
}
