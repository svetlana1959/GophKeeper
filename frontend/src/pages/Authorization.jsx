import styles from './Registration.module.css'
import logo from '../assets/logo.png'
import { Link, useNavigate } from 'react-router-dom'
import regLogo from '../assets/authLogo.svg'
import { useState } from 'react'
import { api, setToken } from '../api/client'

function Authorization() {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const navigate = useNavigate()

    const handleSubmit = async (event) => {
        event.preventDefault()
        setError('')

        if (!username.trim() || !password) {
            setError('Please fill in all fields.')
            return
        }

        setIsSubmitting(true)

        try {
            const response = await api.login(username, password)
            setToken(response.access_token)
            navigate('/')
        } catch (err) {
            setError(err.message || 'Login failed.')
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
                        <img src={regLogo} alt="Log in" />
                    </div>
                    <div className={styles.title}>Welcome back</div>
                    <div className={styles.subtitle}>Log in to manage your secrets and devices.</div>
                    <form onSubmit={handleSubmit}>
                        <label htmlFor="username">Username</label>
                        <input
                            id="username"
                            className={`${styles.input} ${styles.userInput}`}
                            name="username"
                            type="text"
                            autoComplete="username"
                            placeholder="Enter your username"
                            value={username}
                            onChange={(event) => setUsername(event.target.value)}
                        />
                        <label htmlFor="password">Password</label>
                        <div className={styles.inputWrapper}>
                            <input
                                id="password"
                                className={`${styles.input} ${styles.passInput}`}
                                name="password"
                                type="password"
                                autoComplete="current-password"
                                placeholder="Enter your password"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                            />
                        </div>
                        {error ? <div className={styles.errorMessage}>{error}</div> : null}
                        <button className={styles.submitButton} style={{ marginTop: "64px" }} type="submit" disabled={isSubmitting}>
                            {isSubmitting ? 'Logging in...' : 'Log in'}
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