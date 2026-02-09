import { useState } from 'react'
import type { ChatSource } from '../../types'
import { ClipboardList, Scale, ChevronDown, ChevronUp } from 'lucide-react'
import clsx from 'clsx'

interface Props {
  sources: ChatSource[]
}

/**
 * T7-4: 來源展開面板
 * 顯示公司內規 / 勞動法規來源，可收合展開 snippet
 */
export default function SourcePanel({ sources }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (!sources || sources.length === 0) return null

  const policySources = sources.filter(s => s.type === 'policy')
  const lawSources = sources.filter(s => s.type === 'law')

  return (
    <div className="mt-2 border-t border-gray-100 pt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        <span>參考來源 ({sources.length})</span>
        {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>

      {expanded && (
        <div className="mt-2 space-y-2 animate-fade-in">
          {policySources.length > 0 && (
            <div>
              <div className="flex items-center gap-1 text-xs font-medium text-blue-600 mb-1">
                <ClipboardList className="h-3 w-3" />
                公司內規
              </div>
              {policySources.map((s, i) => (
                <SourceCard key={`policy-${i}`} source={s} />
              ))}
            </div>
          )}
          {lawSources.length > 0 && (
            <div>
              <div className="flex items-center gap-1 text-xs font-medium text-emerald-600 mb-1">
                <Scale className="h-3 w-3" />
                勞動法規
              </div>
              {lawSources.map((s, i) => (
                <SourceCard key={`law-${i}`} source={s} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SourceCard({ source }: { source: ChatSource }) {
  const [open, setOpen] = useState(false)

  return (
    <div
      className={clsx(
        'rounded-lg border px-3 py-2 text-xs cursor-pointer transition-colors',
        source.type === 'policy'
          ? 'border-blue-100 bg-blue-50/50 hover:bg-blue-50'
          : 'border-emerald-100 bg-emerald-50/50 hover:bg-emerald-50'
      )}
      onClick={() => setOpen(!open)}
    >
      <div className="flex items-center justify-between">
        <span className="font-medium text-gray-700 truncate">{source.title}</span>
        {source.score != null && (
          <span className="ml-2 shrink-0 text-gray-400">
            {Math.round(source.score * 100)}%
          </span>
        )}
      </div>
      {open && source.snippet && (
        <p className="mt-1.5 text-gray-500 leading-relaxed whitespace-pre-wrap">
          {source.snippet}
        </p>
      )}
    </div>
  )
}
