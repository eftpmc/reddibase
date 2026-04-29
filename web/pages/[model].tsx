import type { GetServerSideProps } from 'next'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { ArrowLeft, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, ExternalLink } from 'lucide-react'
import Layout from '../components/Layout'

interface Model {
  id: string
  display_name: string
  description: string
  subreddit: string
  hf_repo: string
  confirmed_pairs: number
}

interface Stats {
  total: number
  with_flair: number
  without_flair: number
  unique_answers: number
  avg_confidence: number
  min_date: number
  max_date: number
  top_answers: { answer: string; count: number }[]
}

interface DatasetItem {
  post_id: string
  subreddit: string
  description: string
  answer: string
  flair: string | null
  confidence: number
  created_utc: number
}

interface DatasetPage {
  total: number
  page: number
  page_size: number
  items: DatasetItem[]
}

function redditUrl(subreddit: string, postId: string) {
  return `https://reddit.com/r/${subreddit}/comments/${postId}/`
}

function formatDate(ts: number) {
  return new Date(ts * 1000).toLocaleDateString('en-US', { year: 'numeric', month: 'short' })
}

function displayAnswer(flair: string | null, answer: string): string {
  if (flair) return flair
  const first = answer.split(/[\n.!?]/)[0].trim()
  return first.length > 72 ? first.slice(0, 72) + '…' : first
}

export default function ModelPage({ model }: { model: Model }) {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    fetch(`/api/models/${model.id}/dataset/stats`)
      .then(r => r.ok ? r.json() : null)
      .then(setStats)
  }, [model.id])

  return (
    <Layout title={`${model.display_name} — Dataset`}>
      <div className="max-w-4xl mx-auto px-6 py-8">

        {/* Back + meta row */}
        <div className="flex items-center justify-between mb-8">
          <Link href="/models" className="flex items-center gap-1 text-sm text-base-content/40 hover:text-base-content transition-colors">
            <ArrowLeft size={14} /> Models
          </Link>
          <div className="flex items-center gap-3">
            {stats && (
              <span className="text-xs text-base-content/25 tabular-nums hidden sm:inline">
                {stats.total.toLocaleString()} pairs
              </span>
            )}
            <a
              href={`https://reddit.com/r/${model.subreddit}`}
              target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-base-content/40 hover:text-base-content transition-colors"
            >
              r/{model.subreddit} <ExternalLink size={11} />
            </a>
            <a
              href={`https://huggingface.co/${model.hf_repo}`}
              target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-base-content/40 hover:text-base-content transition-colors"
            >
              HF Hub <ExternalLink size={11} />
            </a>
          </div>
        </div>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold mb-1">{model.display_name} — Dataset</h1>
          {model.description && (
            <p className="text-base-content/40 text-sm">{model.description}</p>
          )}
        </div>

        {/* Stats */}
        {stats ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
            {[
              {
                label: 'Total pairs',
                value: stats.total.toLocaleString(),
                sub: `${stats.with_flair.toLocaleString()} flaired · ${stats.without_flair.toLocaleString()} recovered`,
              },
              { label: 'Unique answers', value: stats.unique_answers.toLocaleString() },
              { label: 'Avg confidence', value: `${(stats.avg_confidence * 100).toFixed(0)}%` },
              { label: 'Date range', value: formatDate(stats.min_date), sub: `to ${formatDate(stats.max_date)}` },
            ].map(s => (
              <div key={s.label} className="bg-base-200 rounded-xl p-4 border border-base-300">
                <div className="text-xs text-base-content/40 uppercase tracking-wider mb-1">{s.label}</div>
                <div className="text-xl font-bold tabular-nums">{s.value}</div>
                {s.sub && <div className="text-xs text-base-content/40 mt-1">{s.sub}</div>}
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-base-200 rounded-xl p-4 border border-base-300 animate-pulse h-20" />
            ))}
          </div>
        )}

        <DatasetPanel modelId={model.id} />

      </div>
    </Layout>
  )
}

function DatasetPanel({ modelId }: { modelId: string }) {
  const [data, setData] = useState<DatasetPage | null>(null)
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [minConfidence, setMinConfidence] = useState(0)
  const [maxConfidence, setMaxConfidence] = useState(1)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [source, setSource] = useState('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => { fetchPage(1) }, [])

  async function fetchPage(p: number) {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(p), page_size: '50' })
      if (q) params.set('q', q)
      if (minConfidence > 0) params.set('min_confidence', String(minConfidence))
      if (maxConfidence < 1) params.set('max_confidence', String(maxConfidence))
      if (source !== 'all') params.set('source', source)
      if (dateFrom) params.set('date_from', String(Math.floor(new Date(dateFrom).getTime() / 1000)))
      if (dateTo) params.set('date_to', String(Math.floor(new Date(dateTo + 'T23:59:59').getTime() / 1000)))
      const res = await fetch(`/api/models/${modelId}/dataset?${params}`)
      if (res.ok) { setData(await res.json()); setPage(p) }
    } finally {
      setLoading(false)
    }
  }

  function applyFilters(e: React.FormEvent) {
    e.preventDefault()
    fetchPage(1)
  }

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0

  function pageRange(current: number, total: number): (number | '…')[] {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
    if (current <= 4) return [1, 2, 3, 4, 5, '…', total]
    if (current >= total - 3) return [1, '…', total - 4, total - 3, total - 2, total - 1, total]
    return [1, '…', current - 1, current, current + 1, '…', total]
  }

  return (
    <div>
      <form onSubmit={applyFilters} className="flex flex-col gap-2 mb-6 p-4 bg-base-200 rounded-xl border border-base-300">
        {/* Row 1: search */}
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Search descriptions and answers…"
            value={q}
            onChange={e => setQ(e.target.value)}
            className="input input-bordered input-sm flex-1"
          />
          <button type="submit" className="btn btn-sm btn-primary shrink-0">Apply</button>
        </div>
        {/* Row 2: confidence + source */}
        <div className="flex flex-wrap gap-2">
          <div className="flex items-center gap-1 flex-1 min-w-0">
            <span className="text-xs text-base-content/40 shrink-0">Confidence</span>
            <select className="select select-bordered select-xs flex-1" value={minConfidence} onChange={e => setMinConfidence(Number(e.target.value))}>
              <option value={0}>0%</option>
              <option value={0.5}>50%</option>
              <option value={0.6}>60%</option>
              <option value={0.7}>70%</option>
              <option value={0.75}>75%</option>
              <option value={0.8}>80%</option>
              <option value={0.85}>85%</option>
              <option value={0.9}>90%</option>
              <option value={0.95}>95%</option>
            </select>
            <span className="text-xs text-base-content/40 shrink-0">–</span>
            <select className="select select-bordered select-xs flex-1" value={maxConfidence} onChange={e => setMaxConfidence(Number(e.target.value))}>
              <option value={0.6}>60%</option>
              <option value={0.7}>70%</option>
              <option value={0.75}>75%</option>
              <option value={0.8}>80%</option>
              <option value={0.85}>85%</option>
              <option value={0.9}>90%</option>
              <option value={0.95}>95%</option>
              <option value={1}>100%</option>
            </select>
          </div>
          <select className="select select-bordered select-xs" value={source} onChange={e => setSource(e.target.value)}>
            <option value="all">All sources</option>
            <option value="flaired">Flair</option>
            <option value="classifier">Classifier</option>
          </select>
        </div>
        {/* Row 3: dates + downloads */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1 flex-1 min-w-0">
            <span className="text-xs text-base-content/40 shrink-0">Date</span>
            <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="input input-bordered input-xs flex-1 min-w-0" />
            <span className="text-xs text-base-content/40 shrink-0">–</span>
            <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="input input-bordered input-xs flex-1 min-w-0" />
          </div>
          <div className="flex gap-1 shrink-0">
            <a href={`/api/models/${modelId}/dataset/download?fmt=json`} className="btn btn-xs btn-ghost opacity-50 hover:opacity-100">JSON</a>
            <a href={`/api/models/${modelId}/dataset/download?fmt=csv`} className="btn btn-xs btn-ghost opacity-50 hover:opacity-100">CSV</a>
          </div>
        </div>
      </form>

      {!data && loading && (
        <div className="flex justify-center py-20">
          <span className="loading loading-spinner loading-lg opacity-40" />
        </div>
      )}

      {data && (
        <>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-base-content/40 tabular-nums">
              {data.total.toLocaleString()} pairs
              {loading && <span className="loading loading-dots loading-xs ml-2 opacity-40" />}
            </p>
            {totalPages > 1 && (
              <p className="text-xs text-base-content/40 tabular-nums">Page {page} of {totalPages}</p>
            )}
          </div>

          <div className="overflow-x-auto rounded-xl border border-base-300">
            <table className="table table-sm">
              <thead className="bg-base-200">
                <tr>
                  <th className="w-48">Answer</th>
                  <th>Description</th>
                  <th className="w-24 text-center">Confidence</th>
                  <th className="w-24">Date</th>
                  <th className="w-10"></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map(item => (
                  <tr key={item.post_id} className="hover border-base-300">
                    <td>
                      <span className="font-medium text-sm leading-snug">{displayAnswer(item.flair, item.answer)}</span>
                    </td>
                    <td>
                      <p className="line-clamp-2 text-base-content/50 text-xs leading-relaxed">{item.description}</p>
                    </td>
                    <td className="text-center">
                      <div className={`badge badge-sm tabular-nums badge-outline ${item.confidence >= 0.9 ? 'badge-success' : 'badge-warning'}`}>
                        {(item.confidence * 100).toFixed(0)}%
                      </div>
                    </td>
                    <td className="text-xs text-base-content/40">
                      {item.created_utc ? formatDate(item.created_utc) : '—'}
                    </td>
                    <td>
                      <a
                        href={redditUrl(item.subreddit, item.post_id)}
                        target="_blank" rel="noopener noreferrer"
                        className="text-base-content/30 hover:text-base-content transition-colors"
                        title="View on Reddit"
                      >
                        <ExternalLink size={13} />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-1 mt-6 flex-wrap">
              <button className="btn btn-sm btn-ghost btn-square" onClick={() => fetchPage(1)} disabled={page <= 1 || loading}><ChevronsLeft size={14} /></button>
              <button className="btn btn-sm btn-ghost btn-square" onClick={() => fetchPage(page - 1)} disabled={page <= 1 || loading}><ChevronLeft size={14} /></button>
              {pageRange(page, totalPages).map((p, i) =>
                p === '…'
                  ? <span key={`ellipsis-${i}`} className="px-1 text-sm text-base-content/30">…</span>
                  : <button
                      key={p}
                      onClick={() => fetchPage(p as number)}
                      disabled={loading}
                      className={`btn btn-sm btn-square tabular-nums ${page === p ? 'btn-primary' : 'btn-ghost'}`}
                    >{p}</button>
              )}
              <button className="btn btn-sm btn-ghost btn-square" onClick={() => fetchPage(page + 1)} disabled={page >= totalPages || loading}><ChevronRight size={14} /></button>
              <button className="btn btn-sm btn-ghost btn-square" onClick={() => fetchPage(totalPages)} disabled={page >= totalPages || loading}><ChevronsRight size={14} /></button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export const getServerSideProps: GetServerSideProps = async ({ params }) => {
  const modelId = params?.model as string
  try {
    const res = await fetch(`${process.env.API_URL || 'http://localhost:8000'}/models`)
    const models: Model[] = await res.json()
    const model = models.find(m => m.id === modelId)
    if (!model) return { notFound: true }
    return { props: { model } }
  } catch {
    return { notFound: true }
  }
}
