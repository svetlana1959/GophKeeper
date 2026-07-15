import { Link } from 'react-router-dom'
import { buttonVariants } from '@/components/ui/button-variants'
import { BrandLogo } from '@/components/brand/logo'
import { GITHUB_URL, NAV_LINKS } from '../constants'

export function LandingHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-[#08090b]/80 backdrop-blur-md">
      <div className="mx-auto flex h-18 max-w-7xl items-center justify-between px-6 py-4">
        <Link
          to="/"
          aria-label="GophKeeper home"
          className="focus-visible:ring-primary rounded focus-visible:ring-2 focus-visible:outline-none"
        >
          <BrandLogo className="[&_span]:text-2xl" />
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map(({ label, href }) => (
            <a
              key={href}
              href={href}
              className="text-sm font-medium text-white/60 transition-colors hover:text-white"
            >
              {label}
            </a>
          ))}
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className="text-sm font-medium text-white/60 transition-colors hover:text-white"
          >
            GitHub
          </a>
        </nav>

        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="hidden text-sm font-medium text-white/70 transition-colors hover:text-white sm:inline"
          >
            Log in
          </Link>
          <Link to="/register" className={buttonVariants({ size: 'default' })}>
            Get Started
          </Link>
        </div>
      </div>
    </header>
  )
}
