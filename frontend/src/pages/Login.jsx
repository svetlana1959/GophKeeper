import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, setToken } from '../api/client'
import styles from './Auth.module.css'

function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const { access_token } = await api.login(email, password)
      setToken(access_token)
      navigate('/account')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.brand}>
          Goph<span className={styles.accent}>Keeper</span>
        </div>
        <div className={styles.title}>Welcome back</div>
        <div className={styles.subtitle}>Log in to manage your account and devices.</div>
        <form onSubmit={onSubmit}>
          <label className={styles.label} htmlFor="email">Email</label>
          <input
            id="email"
            className={styles.input}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />
          <label className={styles.label} htmlFor="password">Password</label>
          <input
            id="password"
            className={styles.input}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Your password"
            required
          />
          <button className={styles.button} type="submit" disabled={busy}>
            {busy ? 'Logging in…' : 'Log in'}
          </button>
        </form>
        {error && <div className={styles.error}>{error}</div>}
        <div className={styles.footer}>
          Don&apos;t have an account? <Link to="/register">Create account</Link>
        </div>
      </div>
    </div>
  )
}

export default Login
