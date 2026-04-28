import type { GetServerSideProps } from 'next'
import Head from 'next/head'
import Link from 'next/link'
import { useEffect, useState } from 'react'

interface Model {
  id: string
  display_name: string
  description: string
  subreddit: string
  hf_repo: string
  confirmed_pairs: number
}

interface SearchResult {
  post_id: string
  description: string
  answer: string
  flair: string | null
  confidence: number
  similarity: number
  created_utc: number
}

interface DatasetItem {
  post_id: string
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

interface Props {
  model: Model
}

export default function ModelPage({ model }: Props) {
  const [tab, setTab] = useState<'search' | 'dataset'>('search')

  return (
    <>
      <Head>
        <title>{model.display_name} — Reddibase</title>
      </Head>
      <div className="min-h-screen bg-gray-950 text-white">
        <div className="max-w-4xl mx-auto px-6 py-12">
          <Link href="/" className="text-gray-500 hover:text-gray-300 text-sm mb-6 inline-block">
            ← All models
          </Link>

          <div className="mb-8">
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-3xl font-bold">{model.display_name}</h1>
              <a
                href={`https://reddit.com/r/${model.subreddit}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs bg-gray-800 text-gray-400 hover:text-gray-200 rounded-full px-2 py-0.5"
              >
                r/{model.subreddit}
              </a>
            </div>
            {model.description && (
              <p className="text-gray-400">{model.description}</p>
            )}
            <div className="flex gap-4 mt-3 text-sm text-gray-500">
              <span>
                <span className="text-white font-medium">
                  {model.confirmed_pairs.toLocaleString()}
                </span>{' '}
                confirmed pairs
              </span>
              <a
                href={`https://huggingface.co/${model.hf_repo}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-500 hover:text-gray-300"
              >
                HF Hub ↗
              </a>
            </div>
          </div>

          <div className="flex gap-1 mb-6 border-b border-gray-800">
            {(['search', 'dataset'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm font-medium capitalize -mb-px border-b-2 transition-colors ${
                  tab === t
                    ? 'border-white text-white'
                    : 'border-transparent text-gray-500 hover:text-gray-300'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {tab === 'search' ? (
            <SearchTab modelId={model.id} />
          ) : (
            <DatasetTab modelId={model.id} />
          )}
        </div>
      </div>
    </>
  )
}

function SearchTab({ modelId }: { modelId: string }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `/api/models/${modelId}/search?q=${encodeURIComponent(query)}&top_k=10`
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        setError(err.detail || `Error ${res.status}`)
        setResults([])
      } else {
        setResults(await res.json())
      }
    } catch (e) {
      setError('Could not reach the API.')
      setResults([])
    } finally {
      setLoading(false)
      setSearched(true)
    }
  }

  return (
    <div>
      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Describe what you're looking for..."
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-gray-500 placeholder:text-gray-600"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-white text-gray-950 font-medium text-sm px-4 py-2.5 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Searching…' : 'Search'}
        </button>
      </form>

      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((r, i) => (
            <div key={r.post_id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="flex items-start justify-between gap-3 mb-2">
                <p className="font-medium text-sm">{r.flair || r.answer}</p>
                <span className="text-xs text-gray-500 shrink-0">
                  {(r.similarity * 100).toFixed(0)}% match
                </span>
              </div>
              <p className="text-gray-400 text-sm line-clamp-3">{r.description}</p>
              {r.flair && r.answer !== r.flair && (
                <p className="text-gray-500 text-xs mt-2 line-clamp-2">{r.answer}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {error && <p className="text-red-400 text-sm">{error}</p>}
      {searched && !error && results.length === 0 && !loading && (
        <p className="text-gray-500 text-sm">No results found.</p>
      )}
    </div>
  )
}

function DatasetTab({ modelId }: { modelId: string }) {
  const [data, setData] = useState<DatasetPage | null>(null)
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => { fetchPage(1, '') }, [])

  async function fetchPage(p: number, q: string) {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(p), page_size: '50' })
      if (q) params.set('q', q)
      const res = await fetch(`/api/models/${modelId}/dataset?${params}`)
      if (res.ok) {
        const json = await res.json()
        setData(json)
        setPage(p)
      }
    } finally {
      setLoading(false)
    }
  }

  function handleFilter(e: React.FormEvent) {
    e.preventDefault()
    fetchPage(1, filter)
  }

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <form onSubmit={handleFilter} className="flex gap-2">
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter pairs..."
            className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-gray-500 placeholder:text-gray-600 w-64"
          />
          <button
            type="submit"
            className="text-sm text-gray-400 hover:text-white px-2 transition-colors"
          >
            Filter
          </button>
        </form>

        <div className="flex gap-2">
          <a
            href={`/api/models/${modelId}/dataset/download?fmt=json`}
            className="text-xs text-gray-500 hover:text-gray-300 border border-gray-800 rounded px-2 py-1"
          >
            JSON
          </a>
          <a
            href={`/api/models/${modelId}/dataset/download?fmt=csv`}
            className="text-xs text-gray-500 hover:text-gray-300 border border-gray-800 rounded px-2 py-1"
          >
            CSV
          </a>
        </div>
      </div>

      {!data && loading && <p className="text-gray-500 text-sm">Loading…</p>}
      {data && <p className="text-xs text-gray-600 mb-3">{data.total?.toLocaleString() ?? '—'} pairs</p>}

      <div className="space-y-2">
        {(data?.items ?? []).map((item) => (
          <div key={item.post_id} className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-sm">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-medium text-white truncate">{item.flair || item.answer}</p>
                <p className="text-gray-500 text-xs mt-0.5 line-clamp-2">{item.description}</p>
              </div>
              <span className="text-xs text-gray-600 shrink-0">
                {(item.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6 text-sm text-gray-500">
          <button
            onClick={() => fetchPage(page - 1, filter)}
            disabled={page <= 1 || loading}
            className="hover:text-white disabled:opacity-30 transition-colors"
          >
            ← Previous
          </button>
          <span>
            {page} / {totalPages}
          </span>
          <button
            onClick={() => fetchPage(page + 1, filter)}
            disabled={page >= totalPages || loading}
            className="hover:text-white disabled:opacity-30 transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}

export const getServerSideProps: GetServerSideProps = async ({ params }) => {
  const modelId = params?.model as string
  const base = process.env.API_URL || 'http://localhost:8000'

  const res = await fetch(`${base}/models`)
  const models: Model[] = await res.json()
  const model = models.find((m) => m.id === modelId)

  if (!model) return { notFound: true }
  return { props: { model } }
}
