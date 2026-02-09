import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'

interface Props {
  content: string
}

/**
 * T7-3: Markdown 渲染元件
 * 支援 GFM 表格、程式碼高亮、清單等
 */
export default function MarkdownRenderer({ content }: Props) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        // 段落
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        // 標題
        h1: ({ children }) => <h1 className="text-lg font-bold mb-2 mt-3">{children}</h1>,
        h2: ({ children }) => <h2 className="text-base font-bold mb-2 mt-3">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-bold mb-1 mt-2">{children}</h3>,
        // 清單
        ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        // 表格
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="min-w-full border-collapse text-sm">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-gray-50">{children}</thead>,
        th: ({ children }) => (
          <th className="border border-gray-200 px-3 py-1.5 text-left font-semibold text-gray-700">{children}</th>
        ),
        td: ({ children }) => (
          <td className="border border-gray-200 px-3 py-1.5 text-gray-600">{children}</td>
        ),
        // 程式碼
        code: ({ className, children, ...props }) => {
          const isBlock = className?.startsWith('language-')
          if (isBlock) {
            return (
              <code className={`${className} block overflow-x-auto rounded bg-gray-900 p-3 text-xs text-gray-100`} {...props}>
                {children}
              </code>
            )
          }
          return (
            <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-mono text-pink-600" {...props}>
              {children}
            </code>
          )
        },
        pre: ({ children }) => <pre className="my-2">{children}</pre>,
        // 引言
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-blue-300 pl-3 my-2 text-gray-600 italic">
            {children}
          </blockquote>
        ),
        // 粗體
        strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
        // 連結
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline hover:text-blue-800">
            {children}
          </a>
        ),
        // 分隔線
        hr: () => <hr className="my-3 border-gray-200" />,
      }}
    >
      {content}
    </ReactMarkdown>
  )
}
