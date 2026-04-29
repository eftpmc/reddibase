import type { GetServerSideProps } from 'next'
import { useRef, useState } from 'react'
import { Search, ExternalLink } from 'lucide-react'
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
  subreddit: string
  description: string
  answer: string
  flair: string | null
  similarity: number
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
  return first.length > 72 ? first.slice(0, 72) + '…' : first
}

export default function Home({ models }: { models: Model[] }) {
  const [query, setQuery] = useState('')
  const [selectedModel, setSelectedModel] = useState(models[0]?.id ?? '')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const active = models.find(m => m.id === selectedModel)
  const examples = EXAMPLES[selectedModel] ?? []

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    const q = query.trim()
    if (!q || !selectedModel) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/models/${selectedModel}/search?q=${encodeURIComponent(q)}&top_k=10`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        setError(err.detail || `Error ${res.status}`)
        setResults([])
      } else {
        setResults(await res.json())
      }
    } catch {
      setError('Could not reach the API.')
      setResults([])
    } finally {
      setLoading(false)
      setSearched(true)
    }
  }

  function useExample(q: string) {
    setQuery(q)
    inputRef.current?.focus()
  }

  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-6 py-16">

        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold tracking-tight mb-2">Can't remember it?</h1>
          <p className="text-base-content/50 text-lg">Describe it. We'll find it.</p>
        </div>

        {models.length === 0 ? (
          <p className="text-center text-base-content/30">No models available yet.</p>
        ) : (
          <>
            <form onSubmit={handleSearch} className="flex gap-2 mb-4">
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder={active ? `Describe a ${active.display_name.toLowerCase()}…` : 'Describe what you\'re looking for…'}
                className="input input-bordered flex-1"
                autoFocus
              />
              <button type="submit" disabled={loading || !query.trim()} className="btn btn-primary px-5">
                {loading ? <span className="loading loading-spinner loading-sm" /> : <Search size={16} />}
              </button>
            </form>

            {models.length > 1 && (
              <div className="flex flex-wrap gap-2 mb-6">
                {models.map(m => (
                  <button
                    key={m.id}
                    onClick={() => setSelectedModel(m.id)}
                    className={`btn btn-sm rounded-full ${selectedModel === m.id ? 'btn-primary' : 'btn-ghost border border-base-300'}`}
                  >
                    {m.display_name}
                  </button>
                ))}
              </div>
            )}

            {error && <div className="alert alert-error mb-4"><span>{error}</span></div>}

            {results.length > 0 && (
              <div className="flex flex-col gap-3 mt-6">
                {results.map((r, i) => (
                  <div key={r.post_id} className="card bg-base-200 border border-base-300 hover:border-base-content/20 transition-colors">
                    <div className="card-body p-5 gap-2">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-mono text-base-content/20 w-4 text-right shrink-0">{i + 1}</span>
                          <p className="font-semibold leading-snug">{displayAnswer(r.flair, r.answer)}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <div className={`badge badge-sm tabular-nums badge-outline ${r.similarity >= 0.8 ? 'badge-primary' : r.similarity >= 0.6 ? 'badge-warning' : 'badge-ghost'}`}>
                            {(r.similarity * 100).toFixed(0)}%
                          </div>
                          <a
                            href={redditUrl(r.subreddit, r.post_id)}
                            target="_blank" rel="noopener noreferrer"
                            className="text-base-content/30 hover:text-base-content transition-colors"
                            title="View on Reddit"
                          >
                            <ExternalLink size={13} />
                          </a>
                        </div>
                      </div>
                      <p className="text-base-content/40 text-sm line-clamp-2 pl-7 leading-relaxed">
                        {r.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {searched && !error && results.length === 0 && !loading && (
              <div className="text-center py-16 text-base-content/30">
                <p className="text-lg mb-1">No matches found</p>
                <p className="text-sm">Try rephrasing or adding more detail</p>
              </div>
            )}

            {!searched && examples.length > 0 && (
              <div className="flex flex-col items-center gap-3 mt-8">
                <p className="text-xs text-base-content/25 uppercase tracking-widest">Try an example</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {examples.map(ex => (
                    <button
                      key={ex}
                      onClick={() => useExample(ex)}
                      className="btn btn-xs btn-ghost text-base-content/40 hover:text-base-content border border-base-300 normal-case"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {!searched && active && (
              <p className="text-center text-xs text-base-content/20 tabular-nums mt-8">
                {active.confirmed_pairs.toLocaleString()} confirmed pairs · r/{active.subreddit}
              </p>
            )}
          </>
        )}
      </div>
    </Layout>
  )
}

export const getServerSideProps: GetServerSideProps = async () => {
  try {
    const res = await fetch(`${process.env.API_URL || 'http://localhost:8000'}/models`)
    const models = await res.json()
    return { props: { models } }
  } catch {
    return { props: { models: [] } }
  }
}
