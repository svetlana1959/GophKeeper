import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import styles from './Registration.module.css'
import logo from '../assets/logo.png'
import regLogo from '../assets/authLogo.svg'
import { api, getToken, setToken } from '../api/client'

function Authorization() {
    const navigate = useNavigate()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const isAuthed = Boolean(getToken())

    if (isAuthed) {
        return <Navigate to="/dashboard" replace />
    }

    const handleSubmit = async (event) => {
        event.preventDefault()
        setError('')
        setIsSubmitting(true)

        try {
            const response = await api.login(email, password)
            setToken(response.access_token)
            navigate('/dashboard', { replace: true })
        } catch (err) {
            setError(err.message || 'Не удалось войти')
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <div className={styles.container}>
            <div className={styles.sidebar}>
                <div className={styles.sidebarTitle}>
                    <img src={logo} alt="lock" />
                    <div className={styles.sidebarTitleText}>
                        <span style={{ color: "#F4F5f5" }}>Goph</span>
                        <span style={{ color: "#008645" }}>Keeper</span>
                    </div>
                </div>
                <div className={styles.sidebarSubtitle} >
                    Secure your secrets. <br />
                    Anywhere. Anytime.
                </div>
            </div>
            <div className={styles.content}>
                <div className={styles.form}>
                    <div className={styles.regLogo}>
                        <img src={regLogo} alt="Registration" />
                    </div>
                    <div className={styles.title}>Sign in</div>
                    <div className={styles.subtitle}>Use your account email and password.</div>
                    <form onSubmit={handleSubmit}>
                        <label htmlFor="email">Email</label>
                        <input
                            className={`${styles.input} ${styles.userInput}`}
                            id="email"
                            name='email'
                            type='email'
                            placeholder='Enter your email'
                            value={email}
                            onChange={(event) => setEmail(event.target.value)}
                            autoComplete="email"
                            required
                        />
                        <label htmlFor="password">Password</label>
                        <div className={styles.inputWrapper}>
                            <input
                                className={`${styles.input} ${styles.passInput}`}
                                id="password"
                                name='password'
                                type='password'
                                placeholder='Enter your password'
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                autoComplete="current-password"
                                required
                            />
                        </div>
                        {error ? <div className={styles.error}>{error}</div> : null}
                        <button className={styles.submitButton} style={{ marginTop: "64px" }} disabled={isSubmitting}>
                            {isSubmitting ? 'Signing in...' : 'Log in'}
                        </button>
                    </form>
                    <div className={styles.hr}>
                        <div className={styles.hrLine}></div>
                        <div className={styles.hrText}>or</div>
                        <div className={styles.hrLine}></div>
                    </div>
                    <div className={styles.footer}>
                        Don't have account? <Link to='/register' style={{ color: "#23BD21", fontWeight: "500" }}>Create account</Link>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Authorization;