import Link from 'next/link'
import { ArrowRight, CheckCircle2, ExternalLink, UploadCloud } from 'lucide-react'
import { FaGithub } from 'react-icons/fa'
import Layout from '../components/Layout'

const steps = [
  {
    title: 'Create threads',
    body: 'Use the scrape notebook or CLI to create a source-neutral threads.jsonl artifact from a human-solved community.',
  },
  {
    title: 'Audit the data',
    body: 'Check message coverage, weak-answer labels, excluded labels, date range, and top answers before spending GPU time.',
  },
  {
    title: 'Extract answers',
    body: 'Train the resolved-thread classifier, then run it over threads to produce confirmed description-answer pairs.',
  },
  {
    title: 'Train identifier',
    body: 'Train the retrieval model from confirmed_pairs.jsonl and build the FAISS search index.',
  },
  {
    title: 'Open a PR',
    body: 'Create models/{subreddit}/config.yaml from the generated config, fill in display_name and description, then submit the PR.',
  },
]

export default function ContributePage() {
  return (
    <Layout title="Contribute">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <section className="mb-10">
          <div className="mb-3 flex items-center gap-2 text-xs uppercase tracking-wider text-base-content/40">
            <UploadCloud size={13} /> Contribution flow
          </div>
          <h1 className="text-3xl font-bold tracking-tight mb-3">Add a model to Reddibase</h1>
          <p className="max-w-2xl text-base-content/55 leading-relaxed">
            Contributors train models outside the web app, publish artifacts to Hugging Face, and add a small config file by pull request.
          </p>
        </section>

        <section className="mb-10 grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-lg border border-base-300 bg-base-200 p-4">
            <h2 className="font-semibold mb-1">You need</h2>
            <p className="text-sm text-base-content/50 leading-relaxed">A Python environment, local or datacenter GPU access, and a Hugging Face account for publishing.</p>
          </div>
          <div className="rounded-lg border border-base-300 bg-base-200 p-4">
            <h2 className="font-semibold mb-1">Good candidates</h2>
            <p className="text-sm text-base-content/50 leading-relaxed">Communities or archives where vague requests regularly receive confirmed answers.</p>
          </div>
          <div className="rounded-lg border border-base-300 bg-base-200 p-4">
            <h2 className="font-semibold mb-1">End result</h2>
            <p className="text-sm text-base-content/50 leading-relaxed">A Hugging Face artifact repo plus one config file in this repository.</p>
          </div>
        </section>

        <section className="mb-10">
          <h2 className="text-xl font-bold tracking-tight mb-4">Steps</h2>
          <div className="flex flex-col gap-3">
            {steps.map((step, index) => (
              <div key={step.title} className="rounded-lg border border-base-300 bg-base-100 p-4">
                <div className="flex gap-3">
                  <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                    {index + 1}
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">{step.title}</h3>
                    <p className="text-sm text-base-content/50 leading-relaxed">{step.body}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-base-300 bg-base-200 p-5">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-xl font-bold tracking-tight mb-1">Ready to start?</h2>
              <p className="text-sm text-base-content/50">Use the split notebooks or CLI pipeline, then submit the generated config.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <a
                href="https://github.com/eftpmc/reddibase/tree/main/notebooks"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary btn-sm gap-2"
              >
                Notebooks <ExternalLink size={13} />
              </a>
              <a
                href="https://github.com/eftpmc/reddibase"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-ghost btn-sm gap-2 border border-base-300"
              >
                <FaGithub size={13} /> GitHub
              </a>
            </div>
          </div>
        </section>

        <div className="mt-6 flex items-center gap-2 text-sm text-base-content/45">
          <CheckCircle2 size={14} />
          <span>Merged configs appear in the model registry automatically.</span>
          <Link href="/models" className="ml-auto flex items-center gap-1 hover:text-base-content">
            View models <ArrowRight size={13} />
          </Link>
        </div>
      </div>
    </Layout>
  )
}
