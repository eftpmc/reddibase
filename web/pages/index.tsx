import type { GetServerSideProps } from 'next'
import Link from 'next/link'
import { ArrowRight, Cpu, Database, ExternalLink, Hash, Layers, Search, UploadCloud } from 'lucide-react'
import Layout from '../components/Layout'

interface Model {
  id: string
  display_name: string
  description: string
  subreddit: string
  hf_repo: string
  classifier_repo: string
  confirmed_pairs: number
}

export default function Home({ models }: { models: Model[] }) {
  const classifierCount = new Set(models.map(m => m.classifier_repo).filter(Boolean)).size
  const pairCount = models.reduce((sum, m) => sum + (m.confirmed_pairs || 0), 0)

  return (
    <Layout>
      <div className="max-w-5xl mx-auto px-6 py-12">
        <section className="pb-12">
          <div className="flex flex-col gap-8 md:flex-row md:items-end md:justify-between">
            <div className="max-w-2xl">
              <div className="mb-3 flex items-center gap-2 text-xs uppercase tracking-wider text-base-content/40">
                <Search size={13} /> Search first
              </div>
              <h1 className="text-4xl font-bold tracking-tight mb-3">Find the thing you half remember</h1>
              <p className="text-lg text-base-content/55 leading-relaxed">
                Search identification models trained from Reddit threads where someone described a forgotten game, object, bug, or story and the community solved it.
              </p>
              <div className="mt-5 flex flex-wrap items-center gap-4 text-sm text-base-content/45">
                <span className="tabular-nums">{models.length.toLocaleString()} models</span>
                <span className="text-base-content/20">/</span>
                <span className="tabular-nums">{pairCount.toLocaleString()} confirmed pairs</span>
                <span className="text-base-content/20">/</span>
                <span className="tabular-nums">{classifierCount.toLocaleString()} classifiers</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href="/search" className="btn btn-primary gap-2">
                <Search size={16} /> Search
              </Link>
              <Link href="/models" className="btn btn-ghost gap-2 border border-base-300">
                Models <ArrowRight size={16} />
              </Link>
            </div>
          </div>
        </section>

        <section className="border-y border-base-300 py-12">
          <div className="mb-5">
            <h2 className="text-xl font-bold tracking-tight">How it works</h2>
            <p className="max-w-2xl text-sm text-base-content/45">
              Reddibase separates model creation from search. Contributors build model artifacts in notebooks; the app reads approved configs and serves fast lookup.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="rounded-lg border border-base-300 bg-base-200 p-4">
              <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-md bg-base-100 text-base-content/60">
                <Database size={16} />
              </div>
              <h3 className="font-semibold mb-1">Collect threads</h3>
              <p className="text-sm text-base-content/50 leading-relaxed">Scrape posts and comments from communities built around identifying half-remembered things.</p>
            </div>
            <div className="rounded-lg border border-base-300 bg-base-200 p-4">
              <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-md bg-base-100 text-base-content/60">
                <Cpu size={16} />
              </div>
              <h3 className="font-semibold mb-1">Recover answers</h3>
              <p className="text-sm text-base-content/50 leading-relaxed">Run classifier inference to find confirmed answer comments and produce description-answer pairs.</p>
            </div>
            <div className="rounded-lg border border-base-300 bg-base-200 p-4">
              <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-md bg-base-100 text-base-content/60">
                <UploadCloud size={16} />
              </div>
              <h3 className="font-semibold mb-1">Ship a model</h3>
              <p className="text-sm text-base-content/50 leading-relaxed">Train a retrieval index, publish artifacts to Hugging Face, and add the model config by PR.</p>
            </div>
          </div>
        </section>

        <section className="border-b border-base-300 py-12">
          <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-xl font-bold tracking-tight">Model Collection</h2>
              <p className="text-sm text-base-content/45">Inspect model datasets, artifact metadata, and the communities each model covers.</p>
            </div>
            <Link href="/models" className="btn btn-sm btn-ghost gap-1.5">
              All models <ArrowRight size={13} />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
            <div className="border border-base-300 bg-base-100 rounded-lg p-4">
              <div className="flex items-center gap-2 text-xs text-base-content/40 uppercase tracking-wider mb-2">
                <Layers size={13} /> Models
              </div>
              <div className="text-2xl font-bold tabular-nums">{models.length.toLocaleString()}</div>
            </div>
            <div className="border border-base-300 bg-base-100 rounded-lg p-4">
              <div className="flex items-center gap-2 text-xs text-base-content/40 uppercase tracking-wider mb-2">
                <Database size={13} /> Confirmed pairs
              </div>
              <div className="text-2xl font-bold tabular-nums">{pairCount.toLocaleString()}</div>
            </div>
            <div className="border border-base-300 bg-base-100 rounded-lg p-4">
              <div className="flex items-center gap-2 text-xs text-base-content/40 uppercase tracking-wider mb-2">
                <Cpu size={13} /> Classifiers
              </div>
              <div className="text-2xl font-bold tabular-nums">{classifierCount.toLocaleString()}</div>
            </div>
          </div>

          {models.length === 0 ? (
            <p className="text-base-content/30">No models registered yet.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {models.slice(0, 6).map(m => (
                <div key={m.id} className="card bg-base-200 border border-base-300 hover:border-base-content/20 transition-colors">
                  <div className="card-body p-5 gap-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="font-bold text-lg leading-tight mb-1">{m.display_name}</h3>
                        <p className="text-sm text-base-content/50 line-clamp-2">
                          {m.description || 'Identification model trained on confirmed Reddit threads.'}
                        </p>
                      </div>
                      <Link href={`/${m.id}`} className="btn btn-sm btn-primary gap-1.5 shrink-0">
                        Open <ArrowRight size={13} />
                      </Link>
                    </div>

                    <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-base-300">
                      <div className="flex items-center gap-1.5 text-sm text-base-content/50">
                        <Hash size={13} className="text-base-content/30" />
                        <span>r/{m.subreddit}</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-sm text-base-content/50">
                        <Database size={13} className="text-base-content/30" />
                        <span className="tabular-nums">{m.confirmed_pairs.toLocaleString()} pairs</span>
                      </div>
                      <a
                        href={`https://huggingface.co/${m.hf_repo}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-auto flex items-center gap-1 text-xs text-base-content/40 hover:text-base-content transition-colors"
                      >
                        HF Hub <ExternalLink size={11} />
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="pt-10">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-xl font-bold tracking-tight">Add a model</h2>
              <p className="text-sm text-base-content/45">Use the notebook workflow to train artifacts, then submit the generated config.</p>
            </div>
            <Link href="/contribute" className="btn btn-sm btn-ghost gap-2 border border-base-300">
              Contribution flow <ArrowRight size={14} />
            </Link>
          </div>
        </section>
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
