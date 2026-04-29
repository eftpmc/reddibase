import Link from 'next/link'
import { ArrowRight, CheckCircle2, ExternalLink, UploadCloud } from 'lucide-react'
import { FaGithub } from 'react-icons/fa'
import Layout from '../components/Layout'

const steps = [
  {
    title: 'Open the notebook',
    body: 'Run notebooks/train.ipynb in Google Colab with a T4 GPU. The notebook handles scraping, training, artifact upload, and config generation.',
  },
  {
    title: 'Configure the run',
    body: 'Enter the subreddit name, Hugging Face repo, and write token. Set a flair strategy only when the subreddit uses special solved flairs.',
  },
  {
    title: 'Let it build',
    body: 'The notebook scrapes archived posts, runs classifier inference, trains the identification model, and builds the FAISS search index.',
  },
  {
    title: 'Publish artifacts',
    body: 'Upload encoder weights, index.faiss, and pairs.jsonl to Hugging Face Hub from the notebook.',
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
            <p className="text-sm text-base-content/50 leading-relaxed">Google Colab, Google Drive, and a Hugging Face account with a write token.</p>
          </div>
          <div className="rounded-lg border border-base-300 bg-base-200 p-4">
            <h2 className="font-semibold mb-1">Good candidates</h2>
            <p className="text-sm text-base-content/50 leading-relaxed">Subreddits where vague descriptions regularly receive confirmed answers.</p>
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
              <p className="text-sm text-base-content/50">Use the notebook as the model factory, then submit the generated config.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <a
                href="https://github.com/eftpmc/reddibase/blob/main/notebooks/train.ipynb"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary btn-sm gap-2"
              >
                Notebook <ExternalLink size={13} />
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
