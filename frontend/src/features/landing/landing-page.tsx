import { LandingHeader } from './components/landing-header'
import { Hero } from './components/hero'
import { Features } from './components/features'
import { HowItWorks } from './components/how-it-works'
import { DeveloperShowcase } from './components/developer-showcase'
import { Cta, LandingFooter } from './components/cta'

// Public marketing page. Committed dark aesthetic regardless of the app theme:
// the `dark` scope makes design tokens resolve to their dark values here.
export function LandingPage() {
  return (
    <div className="dark min-h-screen bg-[#08090b] text-white [color-scheme:dark]">
      <LandingHeader />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <DeveloperShowcase />
        <Cta />
      </main>
      <LandingFooter />
    </div>
  )
}
