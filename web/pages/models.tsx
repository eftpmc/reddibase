import type { GetServerSideProps } from 'next'
import Link from 'next/link'
import { Database, ExternalLink, Hash, Table } from 'lucide-react'
import Layout from '../components/Layout'

interface Model {
  id: string
  display_name: string
  description: string
  subreddit: string
  hf_repo: string
  confirmed_pairs: number
}

export default function ModelsPage({ models }: { models: Model[] }) {
  return (
    <Layout title="Models">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="mb-10">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Models</h1>
          <p className="text-base-content/50">Identification models trained on confirmed Reddit threads.</p>
        </div>

        {models.length === 0 ? (
          <p className="text-base-content/30">No models registered yet.</p>
        ) : (
          <div className="flex flex-col gap-4">
            {models.map(m => (
              <div key={m.id} className="card bg-base-200 border border-base-300 hover:border-base-content/20 transition-colors">
                <div className="card-body p-6 gap-4">

                  {/* Header */}
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="font-bold text-xl mb-1">{m.display_name}</h2>
                      {m.description
                        ? <p className="text-base-content/50 text-sm max-w-xl">{m.description}</p>
                        : <p className="text-base-content/30 text-sm italic">No description.</p>
                      }
                    </div>
                    <Link
                      href={`/${m.id}`}
                      className="btn btn-sm btn-primary gap-1.5 shrink-0"
                    >
                      <Table size={13} /> Dataset
                    </Link>
                  </div>

                  {/* Stats row */}
                  <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-base-300">
                    <div className="flex items-center gap-1.5 text-sm text-base-content/50">
                      <Hash size={13} className="text-base-content/30" />
                      <span>r/{m.subreddit}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-sm text-base-content/50">
                      <Database size={13} className="text-base-content/30" />
                      <span>
                        <span className="text-base-content font-medium tabular-nums">{m.confirmed_pairs.toLocaleString()}</span> confirmed pairs
                      </span>
                    </div>
                    <div className="ml-auto">
                      <a
                        href={`https://huggingface.co/${m.hf_repo}`}
                        target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-base-content/40 hover:text-base-content transition-colors"
                      >
                        HF Hub <ExternalLink size={11} />
                      </a>
                    </div>
                  </div>

                </div>
              </div>
            ))}
          </div>
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
