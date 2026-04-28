import type { GetServerSideProps } from 'next'
import Head from 'next/head'
import Link from 'next/link'

interface Model {
  id: string
  display_name: string
  description: string
  subreddit: string
  hf_repo: string
  confirmed_pairs: number
}

interface Props {
  models: Model[]
}

export default function Home({ models }: Props) {
  return (
    <>
      <Head>
        <title>Reddibase</title>
      </Head>
      <div className="min-h-screen bg-gray-950 text-white">
        <div className="max-w-5xl mx-auto px-6 py-16">
          <div className="mb-12">
            <h1 className="text-4xl font-bold tracking-tight mb-2">Reddibase</h1>
            <p className="text-gray-400 text-lg">
              Open-source identification models built from Reddit archives.
            </p>
          </div>

          {models.length === 0 ? (
            <p className="text-gray-500">No models registered yet.</p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {models.map((m) => (
                <Link key={m.id} href={`/${m.id}`}>
                  <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-gray-600 transition-colors cursor-pointer h-full">
                    <div className="flex items-start justify-between mb-3">
                      <h2 className="font-semibold text-lg leading-tight">{m.display_name}</h2>
                      <span className="text-xs bg-gray-800 text-gray-400 rounded-full px-2 py-0.5 ml-2 shrink-0">
                        r/{m.subreddit}
                      </span>
                    </div>
                    {m.description && (
                      <p className="text-gray-400 text-sm mb-4 line-clamp-2">{m.description}</p>
                    )}
                    <p className="text-sm text-gray-500">
                      <span className="text-white font-medium">
                        {m.confirmed_pairs.toLocaleString()}
                      </span>{' '}
                      confirmed pairs
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
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
