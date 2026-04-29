import type { GetServerSideProps } from 'next'
import { Cpu, ExternalLink, Layers } from 'lucide-react'
import Layout from '../components/Layout'

interface Classifier {
  repo: string
  name: string
  used_by: string[]
}

interface Model {
  id: string
  display_name: string
  classifier_repo: string
}

export default function ClassifiersPage({ classifiers }: { classifiers: Classifier[] }) {
  return (
    <Layout title="Classifiers">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="mb-10">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Classifiers</h1>
          <p className="text-base-content/50">
            Solved-thread classifiers that label Reddit posts for training. A single classifier can serve multiple identification models.
          </p>
        </div>

        {classifiers.length === 0 ? (
          <p className="text-base-content/30">No classifiers registered yet.</p>
        ) : (
          <div className="flex flex-col gap-4">
            {classifiers.map(c => (
              <div key={c.repo} className="card bg-base-200 border border-base-300 hover:border-base-content/20 transition-colors">
                <div className="card-body p-6 gap-4">

                  {/* Header */}
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="font-bold text-xl mb-0.5">{c.name}</h2>
                      <p className="text-xs font-mono text-base-content/35">{c.repo}</p>
                    </div>
                    <a
                      href={`https://huggingface.co/${c.repo}`}
                      target="_blank" rel="noopener noreferrer"
                      className="btn btn-sm btn-ghost gap-1.5 shrink-0"
                    >
                      HF Hub <ExternalLink size={13} />
                    </a>
                  </div>

                  {/* Stats row */}
                  {c.used_by.length > 0 && (
                    <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-base-300">
                      <div className="flex items-center gap-1.5 text-sm text-base-content/50">
                        <Cpu size={13} className="text-base-content/30" />
                        <span>Classifier</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-sm text-base-content/50">
                        <Layers size={13} className="text-base-content/30" />
                        <span>
                          Used by{' '}
                          {c.used_by.map((m, i) => (
                            <span key={m}>
                              {i > 0 && <span className="text-base-content/30">, </span>}
                              <span className="text-base-content font-medium">{m}</span>
                            </span>
                          ))}
                        </span>
                      </div>
                    </div>
                  )}

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
    const models: Model[] = await res.json()

    const seen: Record<string, Classifier> = {}
    for (const m of models) {
      if (!m.classifier_repo) continue
      if (!seen[m.classifier_repo]) {
        seen[m.classifier_repo] = {
          repo: m.classifier_repo,
          name: m.classifier_repo.split('/')[1],
          used_by: [],
        }
      }
      seen[m.classifier_repo].used_by.push(m.id)
    }

    return { props: { classifiers: Object.values(seen) } }
  } catch {
    return { props: { classifiers: [] } }
  }
}
