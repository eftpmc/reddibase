import Head from 'next/head'
import Link from 'next/link'
import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import { Cpu, Layers, PanelLeft } from 'lucide-react'
import { FaGithub } from 'react-icons/fa'
import { ReactNode } from 'react'

export default function Layout({ children, title }: { children: ReactNode; title?: string }) {
  const router = useRouter()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    setOpen(window.innerWidth >= 768)
  }, [])

  useEffect(() => {
    if (window.innerWidth < 768) setOpen(false)
  }, [router.asPath])

  const path = router.pathname

  const navItems = [
    { label: 'Models', href: '/models', icon: <Layers size={15} /> },
    { label: 'Classifiers', href: '/classifiers', icon: <Cpu size={15} /> },
  ]

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

        {open && (
          <div
            className="fixed inset-0 top-14 z-20 bg-black/40 md:hidden"
            onClick={() => setOpen(false)}
          />
        )}

        <aside
          className={`fixed left-0 top-14 h-[calc(100vh-3.5rem)] w-52 z-20 bg-base-100 border-r border-base-300 flex flex-col transition-transform duration-200 ${
            open ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <div className="flex-1 overflow-y-auto p-3">
            <ul className="flex flex-col gap-0.5">
              {navItems.map(item => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-colors ${
                      path.startsWith(item.href)
                        ? 'bg-primary/10 text-primary font-medium'
                        : 'text-base-content/60 hover:bg-base-200 hover:text-base-content'
                    }`}
                  >
                    {item.icon}
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
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
