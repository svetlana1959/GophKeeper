import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button-variants'
import { cn } from '@/lib/utils'
import { GITHUB_URL } from '../constants'
import { GithubIcon } from './github-icon'
import banner from '@/assets/landing/mainPageBanner.webp'

export function Hero() {
  return (
    <section className="mx-auto grid max-w-7xl items-center gap-12 px-6 pt-16 pb-20 lg:grid-cols-2 lg:pt-24 lg:pb-28">
      <div className="flex flex-col items-start">
        <h1 className="text-5xl leading-[0.95] font-bold tracking-tight sm:text-6xl lg:text-7xl">
          <span className="text-white">Goph</span>
          <span className="text-primary">Keeper</span>
        </h1>
        <p className="mt-5 text-2xl font-semibold text-white sm:text-3xl">
          Distributed secret management
        </p>
        <p className="mt-5 max-w-md text-lg text-white/50">
          Store, sync, and manage your secrets across every trusted device — end-to-end encrypted,
          so only you can read them.
        </p>
        <div className="mt-9 flex flex-wrap gap-4">
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
      </div>

      <div className="relative">
        <div aria-hidden className="bg-primary/20 absolute inset-0 -z-10 rounded-full blur-3xl" />
        <img
          src={banner}
          alt="A shield securing secrets synced across a laptop, phone, and desktop"
          className="mx-auto w-full max-w-xl"
          loading="eager"
        />
      </div>
    </section>
  )
}
