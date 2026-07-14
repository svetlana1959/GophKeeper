import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import styles from './Registration.module.css'
import secureLogo from '../assets/mingcute_safe-lock-line.svg'
import regLogo from '../assets/mdi_account-box-plus-outline.svg'
import eyeIcon from '../assets/mynaui_eye.png'
import { api, getToken, setToken } from '../api/client'

function Registration() {
    const navigate = useNavigate()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [showPass, setShowPass] = useState(false);
    const [error, setError] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const isAuthed = Boolean(getToken())

    if (isAuthed) {
        return <Navigate to="/logout" replace />
    }

    const handleSubmit = async (event) => {
        event.preventDefault()
        setError('')
        setIsSubmitting(true)

        try {
            const response = await api.register(email, password)
            setToken(response.access_token)
            navigate('/')
        } catch (err) {
            setError(err.message || 'Не удалось зарегистрироваться')
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <div className={styles.container}>
            <div className={styles.sidebar}>
                <div className={styles.sidebarTitle}>
                    <img src={secureLogo} alt="lock" />
                    <div className={styles.sidebarTitleText}>
                        <span style={{ color: "#F4F5f5" }}>Goph</span>
                        <span style={{ color: "#23BD21" }}>Keeper</span>
                    </div>
                </div>
                <div className={styles.sidebarSubtitle}>
                    Distributed zero-knowledge secret management.
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
                    <div className={styles.title}>Create your account</div>
                    <div className={styles.subtitle}>Register with your email and a strong password.</div>
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
                                type={showPass ? 'text' : 'password'}
                                placeholder='Create a strong password'
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                autoComplete="new-password"
                                minLength={8}
                                required
                            />
                            <button
                                onClick={(event) => {
                                    event.preventDefault()
                                    setShowPass((prev) => !prev)
                                }}
                                className={styles.showPassButton}
                                type="button"
                            >
                                <img src={eyeIcon} alt="toggle" />
                            </button>
                        </div>
                        {error ? <div className={styles.error}>{error}</div> : null}
                        <button className={styles.submitButton} disabled={isSubmitting}>
                            {isSubmitting ? 'Creating account...' : 'Create account'}
                        </button>
                    </form>
                    <div className={styles.hr}>
                        <div className={styles.hrLine}></div>
                        <div className={styles.hrText}>or</div>
                        <div className={styles.hrLine}></div>
                    </div>
                    <div className={styles.footer}>
                        Already have account? <Link to='/auth' style={{ fontWeight: "500" }}>Log in</Link>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Registration;