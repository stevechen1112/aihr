import { useState } from 'react'
import { ThumbsUp, ThumbsDown } from 'lucide-react'
import { chatApi } from '../../api'
import clsx from 'clsx'
import toast from 'react-hot-toast'

interface Props {
  messageId: string
  initialFeedback?: 'up' | 'down' | null
}

/**
 * T7-5: 回饋按鈕（👍 / 👎）
 */
export default function FeedbackButtons({ messageId, initialFeedback = null }: Props) {
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(initialFeedback)
  const [submitting, setSubmitting] = useState(false)

  const handleFeedback = async (type: 'up' | 'down') => {
    if (submitting) return
    // 如果已選同一個,取消(toggle 效果? — API 是 upsert 所以重複送同值即可)
    // 簡單做法：切換
    const newType = feedback === type ? null : type
    if (newType === null) return // 目前不支援取消，只能切換

    setSubmitting(true)
    try {
      await chatApi.submitFeedback({
        message_id: messageId,
        rating: newType === 'up' ? 2 : 1,
      })
      setFeedback(newType)
    } catch {
      toast.error('回饋提交失敗')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex items-center gap-1 mt-1">
      <button
        onClick={() => handleFeedback('up')}
        disabled={submitting}
        className={clsx(
          'rounded p-1 transition-colors',
          feedback === 'up'
            ? 'text-green-600 bg-green-50'
            : 'text-gray-300 hover:text-green-500 hover:bg-green-50'
        )}
        title="有幫助"
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={() => handleFeedback('down')}
        disabled={submitting}
        className={clsx(
          'rounded p-1 transition-colors',
          feedback === 'down'
            ? 'text-red-500 bg-red-50'
            : 'text-gray-300 hover:text-red-400 hover:bg-red-50'
        )}
        title="需要改善"
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}
