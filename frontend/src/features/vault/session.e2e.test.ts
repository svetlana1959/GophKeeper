import { generateX25519Identity, identityToRecipient } from 'age-encryption'
import { describe, expect, it } from 'vitest'
import { bytesToBase64, sealContent } from './crypto'
import {
  enrollBrowserDevice,
  isAccountRecoveryKey,
  pullAndDecrypt,
  resealVaultToDevice,
} from './session'

// End-to-end against a live backend — the real vault module, real API, real age.
// Skipped in normal runs; drive it with E2E_API=http://localhost:8080/api.
const API = process.env.E2E_API

async function post(path: string, body: unknown, token?: string) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${path} -> ${res.status} ${await res.text()}`)
  return res.json()
}

describe.skipIf(!API)('vault session (e2e)', () => {
  it('browser enrolls, pulls, and decrypts a recovery-sealed secret', async () => {
    // A fresh account with a recovery key.
    const recoveryIdentity = await generateX25519Identity()
    const recoveryRecipient = await identityToRecipient(recoveryIdentity)
    const email = `vault-e2e-${Date.now()}@example.test`
    const { access_token: accountToken } = await post('/accounts', {
      email,
      password: 'hunter2secret',
    })
    await fetch(`${API}/accounts/me/recovery`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accountToken}` },
      body: JSON.stringify({ recovery_pubkey: recoveryRecipient }),
    })

    // The browser makes itself a device.
    const device = await enrollBrowserDevice({
      accountToken,
      deviceName: 'Chrome on Mac',
      baseUrl: API,
    })
    expect(device.deviceToken).toBeTruthy()
    expect(device.recipient).toMatch(/^age1/)

    // Seed a secret sealed to {this device, recovery key}, pushed as the device.
    const ciphertext = await sealContent(
      {
        name: 'github',
        folder: 'work',
        value: new TextEncoder().encode('ghp_xyz'),
        description: 'token',
      },
      [device.recipient, recoveryRecipient],
    )
    const secretId = crypto.randomUUID()
    await post(
      '/sync/push',
      {
        items: [
          {
            id: secretId,
            ciphertext_b64: bytesToBase64(ciphertext),
            recipients: [device.recipient, recoveryRecipient],
          },
        ],
      },
      device.deviceToken,
    )

    // Recovery-key validation: right key true, wrong key false.
    expect(
      await isAccountRecoveryKey({ accountToken, recoveryKey: recoveryIdentity, baseUrl: API }),
    ).toBe(true)
    const wrong = await generateX25519Identity()
    expect(await isAccountRecoveryKey({ accountToken, recoveryKey: wrong, baseUrl: API })).toBe(
      false,
    )

    // Pull + decrypt with the recovery key.
    const secrets = await pullAndDecrypt({
      token: device.deviceToken,
      identity: recoveryIdentity,
      baseUrl: API,
    })
    const github = secrets.find((s) => s.id === secretId)
    expect(github).toBeDefined()
    expect(github!.name).toBe('github')
    expect(github!.folder).toBe('work')
    expect(new TextDecoder().decode(github!.value)).toBe('ghp_xyz')

    // And the browser's OWN device key decrypts it too (it was a recipient).
    const asDevice = await pullAndDecrypt({
      token: device.deviceToken,
      identity: device.identity,
      baseUrl: API,
    })
    expect(asDevice.find((s) => s.id === secretId)?.name).toBe('github')

    // Device-free recovery: the account token alone reads + decrypts (no device
    // enrollment) — so recovery unlock doesn't leave a junk device behind.
    const viaAccount = await pullAndDecrypt({
      token: accountToken,
      identity: recoveryIdentity,
      baseUrl: API,
    })
    expect(viaAccount.find((s) => s.id === secretId)?.name).toBe('github')
  })

  it('recovery restore: reseals the vault so the browser decrypts with its own key', async () => {
    const recoveryIdentity = await generateX25519Identity()
    const recoveryRecipient = await identityToRecipient(recoveryIdentity)
    const email = `restore-e2e-${Date.now()}@example.test`
    const { access_token: accountToken } = await post('/accounts', {
      email,
      password: 'hunter2secret',
    })
    await fetch(`${API}/accounts/me/recovery`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accountToken}` },
      body: JSON.stringify({ recovery_pubkey: recoveryRecipient }),
    })

    // Seed a secret sealed to the recovery key only — the state after every device
    // has lapsed. (A device is needed to push it, then we ignore it.)
    const seeder = await enrollBrowserDevice({ accountToken, deviceName: 'seeder', baseUrl: API })
    const ciphertext = await sealContent(
      { name: 'aws', folder: 'work', value: new TextEncoder().encode('secret-key') },
      [recoveryRecipient],
    )
    const secretId = crypto.randomUUID()
    await post(
      '/sync/push',
      {
        items: [
          { id: secretId, ciphertext_b64: bytesToBase64(ciphertext), recipients: [recoveryRecipient] },
        ],
      },
      seeder.deviceToken,
    )

    // Restore: make a fresh browser a device and reseal everything to it.
    const restored = await resealVaultToDevice({
      accountToken,
      recoveryKey: recoveryIdentity,
      deviceName: 'Chrome on Mac',
      baseUrl: API,
    })
    expect(restored.device.deviceToken).toBeTruthy()
    expect(restored.failed).toBe(0)
    // The reseal decrypted the vault in passing — no re-pull needed.
    expect(restored.secrets.find((s) => s.id === secretId)?.name).toBe('aws')

    // The restored browser now decrypts with its OWN device key — no recovery key.
    const asDevice = await pullAndDecrypt({
      token: restored.device.deviceToken,
      identity: restored.device.identity,
      baseUrl: API,
    })
    const aws = asDevice.find((s) => s.id === secretId)
    expect(aws).toBeDefined()
    expect(aws!.name).toBe('aws')
    expect(new TextDecoder().decode(aws!.value)).toBe('secret-key')

    // Recovery still works after the reseal (recovery key stays a recipient).
    const viaRecovery = await pullAndDecrypt({
      token: accountToken,
      identity: recoveryIdentity,
      baseUrl: API,
    })
    expect(viaRecovery.find((s) => s.id === secretId)?.name).toBe('aws')
  })
})
