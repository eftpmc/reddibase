import Head from 'next/head'
import Link from 'next/link'
import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import { PanelLeft } from 'lucide-react'
import { FaGithub } from 'react-icons/fa'
import { ReactNode } from 'react'

interface SidebarModel {
  id: string
  display_name: string
  subreddit: string
  classifier_repo: string
}

export default function Layout({ children, title }: { children: ReactNode; title?: string }) {
  const router = useRouter()
  const [models, setModels] = useState<SidebarModel[]>([])
  const [open, setOpen] = useState(false)

  const currentModel = router.query.model as string | undefined
  const currentView = router.query.view as string | undefined

  useEffect(() => {
    setOpen(window.innerWidth >= 768)
  }, [])

  useEffect(() => {
    fetch('/api/models')
      .then(r => r.ok ? r.json() : [])
      .then(setModels)
      .catch(() => {})
  }, [])

  // Close sidebar on route change on mobile
  useEffect(() => {
    if (window.innerWidth < 768) setOpen(false)
  }, [router.asPath])

  return (
    <>
      <Head>
        <title>{title ? `${title} — Reddibase` : 'Reddibase'}</title>
      </Head>
      <div className="min-h-screen bg-base-100 flex flex-col">

        <nav className="border-b border-base-300 bg-base-100/80 backdrop-blur sticky top-0 z-30 h-14 flex items-center gap-3 px-4 shrink-0">
          <button
            onClick={() => setOpen(o => !o)}
            className="btn btn-ghost btn-sm btn-square"
            aria-label="Toggle sidebar"
          >
            <PanelLeft size={16} />
          </button>
          <Link href="/" className="font-bold text-lg tracking-tight hover:text-primary transition-colors">
            Reddibase
          </Link>
        </nav>

        {/* Backdrop — mobile only */}
        {open && (
          <div
            className="fixed inset-0 top-14 z-20 bg-black/40 md:hidden"
            onClick={() => setOpen(false)}
          />
        )}

        {/* Sidebar — fixed overlay */}
        <aside
          className={`fixed left-0 top-14 h-[calc(100vh-3.5rem)] w-52 z-20 bg-base-100 border-r border-base-300 flex flex-col transition-transform duration-200 ${
            open ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-5">
            {models.length > 0 && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-base-content/30 mb-2 px-2">
                  Models
                </p>
                <ul className="flex flex-col gap-0.5">
                  {models.map(m => (
                    <li key={m.id}>
                      <Link
                        href={`/${m.id}`}
                        className={`flex items-center px-2 py-1.5 rounded-lg text-sm transition-colors ${
                          currentModel === m.id && !currentView
                            ? 'bg-primary/10 text-primary font-medium'
                            : 'text-base-content/60 hover:bg-base-200 hover:text-base-content'
                        }`}
                      >
                        {m.display_name}
                      </Link>
                      <Link
                        href={`/${m.id}?view=dataset`}
                        className={`flex items-center pl-6 pr-2 py-1 text-xs rounded-lg transition-colors ${
                          currentModel === m.id && currentView === 'dataset'
                            ? 'text-primary'
                            : 'text-base-content/35 hover:text-base-content/60 hover:bg-base-200'
                        }`}
                      >
                        Dataset
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {(() => {
              const classifiers = [...new Set(models.map(m => m.classifier_repo).filter(Boolean))]
              if (!classifiers.length) return null
              return (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest text-base-content/30 mb-2 px-2">
                    Classifiers
                  </p>
                  <ul className="flex flex-col gap-0.5">
                    {classifiers.map(repo => (
                      <li key={repo}>
                        <a
                          href={`https://huggingface.co/${repo}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center px-2 py-1.5 rounded-lg text-sm text-base-content/60 hover:bg-base-200 hover:text-base-content transition-colors"
                        >
                          {repo.split('/')[1]}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })()}
          </div>

          <div className="p-4 border-t border-base-300 shrink-0">
            <a
              href="https://github.com/eftpmc/reddibase"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm text-base-content/35 hover:text-base-content transition-colors"
            >
              <FaGithub size={15} /> GitHub
            </a>
          </div>
        </aside>

        <main className="flex-1">{children}</main>

      </div>
    </>
  )
}
