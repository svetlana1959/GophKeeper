import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button-variants'
import { cn } from '@/lib/utils'
import { BrandLogo } from '@/components/brand/logo'
import { GITHUB_URL } from '../constants'
import { GithubIcon } from './github-icon'

export function Cta() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-20 lg:py-28">
      <div className="mx-auto max-w-3xl text-center">
        <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
          <span className="text-white">Ready to take </span>
          <span className="text-primary">control</span>
          <span className="text-white"> of your secrets?</span>
        </h2>
        <p className="mx-auto mt-5 max-w-xl text-lg text-white/50">
          Join developers who trust GophKeeper to keep their secrets safe and in sync.
        </p>
      </div>
      <div className="mt-10 flex flex-wrap justify-center gap-4">
        <Link to="/register" className={buttonVariants({ size: 'lg' })}>
          Get Started
          <ArrowRight className="size-4" />
        </Link>
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noreferrer"
          className={cn(
            buttonVariants({ variant: 'outline', size: 'lg' }),
            'border-white/25 bg-transparent text-white hover:bg-white/5 hover:text-white',
          )}
        >
          <GithubIcon className="size-4" />
          View on GitHub
        </a>
      </div>
    </section>
  )
}

export function LandingFooter() {
  return (
    <footer className="border-t border-white/5">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-6 py-8 sm:flex-row">
        <BrandLogo className="[&_span]:text-xl" />
        <p className="text-sm text-white/40">Zero-knowledge secret management.</p>
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 text-sm text-white/50 transition-colors hover:text-white"
        >
          <GithubIcon className="size-4" />
          GitHub
        </a>
      </div>
    </footer>
  )
}
