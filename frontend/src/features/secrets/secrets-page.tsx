import { useVault } from '@/features/vault/vault-context'
import { VaultLockedScreen } from '@/features/vault/locked-screen'
import { VaultSecretsView } from '@/features/vault/secrets-view'

export function SecretsPage() {
  const { status } = useVault()

  return (
    <div className="mx-auto max-w-[1400px]">
      <header>
        <h1 className="text-foreground text-4xl font-bold">Secrets</h1>
        <p className="text-muted-foreground mt-2 text-lg">
          {status === 'unlocked'
            ? 'Decrypted in this browser — values never touch the server.'
            : 'Unlock to decrypt your vault in this browser.'}
        </p>
      </header>

      <div className="mt-8">
        {status === 'unlocked' ? <VaultSecretsView /> : <VaultLockedScreen />}
      </div>
    </div>
  )
}
