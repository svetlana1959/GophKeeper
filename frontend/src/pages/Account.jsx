import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, clearToken, getToken } from '../api/client'
import styles from './Auth.module.css'

function Account() {
  const navigate = useNavigate()
  const [account, setAccount] = useState(null)
  const [invite, setInvite] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!getToken()) {
      navigate('/login')
      return
    }
    api
      .me()
      .then(setAccount)
      .catch(() => {
        clearToken()
        navigate('/login')
      })
  }, [navigate])

  async function linkDevice() {
    setError('')
    setBusy(true)
    try {
      setInvite(await api.createInvite())
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  function logout() {
    clearToken()
    navigate('/login')
  }

  if (!account) return null

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.row}>
          <div className={styles.brand}>
            Goph<span className={styles.accent}>Keeper</span>
          </div>
          <button className={styles.linkButton} onClick={logout}>Log out</button>
        </div>
        <div className={styles.title}>Your account</div>
        <div className={styles.meta}>ID: {account.id}</div>
        <div className={styles.meta}>
          Recovery key: {account.recovery_pubkey ? 'set' : 'not set'}
        </div>

        <button className={styles.button} onClick={linkDevice} disabled={busy}>
          {busy ? 'Generating…' : 'Link a device'}
        </button>
        {error && <div className={styles.error}>{error}</div>}

        {invite && (
          <>
            <div className={styles.code}>goph link {invite.code}</div>
            <div className={styles.hint}>
              Run this on your device. Single use, expires{' '}
              {new Date(invite.expires_at).toLocaleTimeString()}.
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default Account
