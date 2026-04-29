import type { GetServerSideProps } from 'next'
import Link from 'next/link'
import { useRouter } from 'next/router'
import { useEffect, useRef, useState } from 'react'
import { Check, ChevronDown, Database, ExternalLink, Layers, Search as SearchIcon } from 'lucide-react'
import Layout from '../components/Layout'

interface Model {
  id: string
  display_name: string
  description: string
  subreddit: string
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

const EXAMPLES: Record<string, string[]> = {
  tipofmyjoystick: [
    'old DOS game where you play as a knight collecting gems',
    'puzzle game where you push blocks to trap monsters',
    'space shooter defending a planet from waves of aliens',
  ],
}

function redditUrl(subreddit: string, postId: string) {
  return `https://reddit.com/r/${subreddit}/comments/${postId}/`
}

function displayAnswer(flair: string | null, answer: string): string {
  if (flair) return flair
  const first = answer.split(/[\n.!?]/)[0].trim()
  return first.length > 72 ? first.slice(0, 72) + '...' : first
}

export default function SearchPage({
  models,
  initialModel,
  initialQuery,
}: {
  models: Model[]
  initialModel: string
  initialQuery: string
}) {
  const router = useRouter()
  const [modelId, setModelId] = useState(initialModel || models[0]?.id || '')
  const [query, setQuery] = useState(initialQuery)
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [modelOpen, setModelOpen] = useState(false)
  const searchedInitial = useRef(false)
  const modelMenuRef = useRef<HTMLDivElement>(null)

  const active = models.find(m => m.id === modelId)
  const examples = EXAMPLES[modelId] ?? []

  useEffect(() => {
    if (searchedInitial.current || !initialQuery || !modelId) return
    searchedInitial.current = true
    runSearch(initialQuery, modelId, false)
  }, [initialQuery, modelId])

  useEffect(() => {
    function closeModelMenu(event: MouseEvent) {
      if (!modelMenuRef.current?.contains(event.target as Node)) {
        setModelOpen(false)
      }
    }
    document.addEventListener('mousedown', closeModelMenu)
    return () => document.removeEventListener('mousedown', closeModelMenu)
  }, [])

  async function runSearch(q: string, selectedModel: string, updateUrl = true) {
    const trimmed = q.trim()
    if (!trimmed || !selectedModel) return

    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/models/${selectedModel}/search?q=${encodeURIComponent(trimmed)}&top_k=10`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        setError(err.detail || `Error ${res.status}`)
        setResults([])
      } else {
        setResults(await res.json())
        if (updateUrl) {
          router.replace(
            { pathname: '/search', query: { model: selectedModel, q: trimmed } },
            undefined,
            { shallow: true }
          )
        }
      }
    } catch {
      setError('Could not reach the API.')
      setResults([])
    } finally {
      setLoading(false)
      setSearched(true)
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    runSearch(query, modelId)
  }

  function useExample(example: string) {
    setQuery(example)
    runSearch(example, modelId)
  }

  return (
    <Layout title="Search">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Search</h1>
          <p className="text-base-content/50">Choose a model, describe what you remember, and compare ranked matches.</p>
        </div>

        {models.length === 0 ? (
          <p className="text-base-content/30">No models available yet.</p>
        ) : (
          <>
            <form onSubmit={handleSearch} className="mb-5">
              <div className="rounded-2xl border border-base-300 bg-base-100 shadow-sm focus-within:border-primary/45 focus-within:shadow-md transition-all">
                <textarea
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder={active ? `Describe something from r/${active.subreddit}` : 'Describe what you are looking for'}
                  className="textarea w-full min-h-28 resize-none border-0 bg-transparent p-5 text-base leading-relaxed focus:outline-none"
                  autoFocus
                />

                <div className="flex flex-col gap-3 border-t border-base-300 px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="relative" ref={modelMenuRef}>
                    <button
                      type="button"
                      onClick={() => setModelOpen(open => !open)}
                      className="btn btn-sm btn-ghost justify-start gap-2 max-w-full px-2"
                      aria-haspopup="listbox"
                      aria-expanded={modelOpen}
                    >
                      <Layers size={14} className="text-base-content/45 shrink-0" />
                      <span className="truncate">{active?.display_name || 'Choose model'}</span>
                      <ChevronDown size={14} className="text-base-content/40 shrink-0" />
                    </button>

                    {modelOpen && (
                      <div
                        className="absolute left-0 top-10 z-20 w-[min(22rem,calc(100vw-3rem))] overflow-hidden rounded-lg border border-base-300 bg-base-100 shadow-xl"
                        role="listbox"
                      >
                        <div className="max-h-72 overflow-y-auto p-1">
                          {models.map(model => (
                            <button
                              key={model.id}
                              type="button"
                              onClick={() => {
                                setModelId(model.id)
                                setModelOpen(false)
                              }}
                              className={`flex w-full items-start gap-3 rounded-md px-3 py-2.5 text-left transition-colors ${
                                model.id === modelId
                                  ? 'bg-primary/10 text-primary'
                                  : 'hover:bg-base-200 text-base-content'
                              }`}
                              role="option"
                              aria-selected={model.id === modelId}
                            >
                              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center">
                                {model.id === modelId && <Check size={15} />}
                              </span>
                              <span className="min-w-0 flex-1">
                                <span className="block truncate text-sm font-medium">{model.display_name}</span>
                                <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-base-content/45">
                                  <span>r/{model.subreddit}</span>
                                  <span className="tabular-nums">{model.confirmed_pairs.toLocaleString()} pairs</span>
                                </span>
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={loading || !query.trim() || !modelId}
                    className="btn btn-primary btn-sm gap-2 sm:w-auto"
                  >
                    {loading ? <span className="loading loading-spinner loading-xs" /> : <SearchIcon size={15} />}
                    Search
                  </button>
                </div>
              </div>
            </form>

            {active && (
              <div className="flex flex-wrap items-center gap-3 mb-6 px-1 text-sm text-base-content/45">
                <Link href={`/${active.id}`} className="hover:text-base-content transition-colors">
                  r/{active.subreddit}
                </Link>
                <span className="text-base-content/20">/</span>
                <span className="flex items-center gap-1.5 tabular-nums">
                  <Database size={13} className="text-base-content/30" />
                  {active.confirmed_pairs.toLocaleString()} confirmed pairs
                </span>
              </div>
            )}

            {!searched && examples.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 mb-8">
                <span className="text-xs text-base-content/35 uppercase tracking-wider">Examples</span>
                {examples.map(example => (
                  <button
                    key={example}
                    onClick={() => useExample(example)}
                    className="btn btn-xs btn-ghost text-base-content/45 hover:text-base-content border border-base-300 normal-case"
                  >
                    {example}
                  </button>
                ))}
              </div>
            )}

            {error && <div className="alert alert-error mb-4"><span>{error}</span></div>}

            {results.length > 0 && active && (
              <div className="flex flex-col gap-3">
                {results.map((result, index) => (
                  <div key={result.post_id} className="card bg-base-200 border border-base-300 hover:border-base-content/20 transition-colors">
                    <div className="card-body p-5 gap-2">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="text-xs font-mono text-base-content/20 w-4 text-right shrink-0">{index + 1}</span>
                          <p className="font-semibold leading-snug">{displayAnswer(result.flair, result.answer)}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <div className={`badge badge-sm tabular-nums badge-outline ${result.similarity >= 0.8 ? 'badge-primary' : result.similarity >= 0.6 ? 'badge-warning' : 'badge-ghost'}`}>
                            {(result.similarity * 100).toFixed(0)}%
                          </div>
                          <a
                            href={redditUrl(active.subreddit, result.post_id)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-base-content/30 hover:text-base-content transition-colors"
                            title="View on Reddit"
                          >
                            <ExternalLink size={13} />
                          </a>
                        </div>
                      </div>
                      <p className="text-base-content/45 text-sm line-clamp-2 pl-7 leading-relaxed">
                        {result.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {searched && !error && results.length === 0 && !loading && (
              <div className="text-center py-16 text-base-content/30 border border-dashed border-base-300 rounded-lg">
                <p className="text-lg mb-1">No matches found</p>
                <p className="text-sm">Try rephrasing or adding more detail</p>
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  )
}

export const getServerSideProps: GetServerSideProps = async ({ query }) => {
  try {
    const res = await fetch(`${process.env.API_URL || 'http://localhost:8000'}/models`)
    const models: Model[] = await res.json()
    const requestedModel = typeof query.model === 'string' ? query.model : ''
    const initialModel = models.some(model => model.id === requestedModel) ? requestedModel : models[0]?.id || ''
    const initialQuery = typeof query.q === 'string' ? query.q : ''
    return { props: { models, initialModel, initialQuery } }
  } catch {
    return { props: { models: [], initialModel: '', initialQuery: '' } }
  }
}
