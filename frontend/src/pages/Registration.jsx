import styles from './Registration.module.css'
import secureLogo from '../assets/mingcute_safe-lock-line.svg'
import { Link, useNavigate } from 'react-router-dom'
import regLogo from '../assets/mdi_account-box-plus-outline.svg'
import { useState } from 'react'
import eyeIcon from '../assets/mynaui_eye.png'
import { api, setToken } from '../api/client'

function Registration() {
    const [showPass, setShowPass] = useState(false);
    const [showPassConf, setShowPassConf] = useState(false);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError('');

        if (!username.trim() || !password || !confirmPassword) {
            setError('Please fill in all fields.');
            return;
        }

        if (password.length < 8) {
            setError('Password must be at least 8 characters long.');
            return;
        }

        if (password !== confirmPassword) {
            setError('Passwords do not match.');
            return;
        }

        setIsSubmitting(true);

        try {
            const response = await api.register(username, password);
            setToken(response.access_token);
            navigate('/');
        } catch (err) {
            setError(err.message || 'Registration failed.');
        } finally {
            setIsSubmitting(false);
        }
    };

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
                    <div className={styles.subtitle}>Join GophKeeper and keep your data secure.</div>
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
                                type={showPass ? 'text' : 'password'}
                                autoComplete="new-password"
                                placeholder="Create a strong password"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPass((prev) => !prev)}
                                className={styles.showPassButton}
                            >
                                <img src={eyeIcon} alt="toggle" />
                            </button>
                        </div>
                        <label htmlFor="confirmPassword">Confirm password</label>
                        <div className={styles.inputWrapper}>
                            <input
                                id="confirmPassword"
                                className={`${styles.input} ${styles.passInput}`}
                                name="confirmPassword"
                                type={showPassConf ? 'text' : 'password'}
                                autoComplete="new-password"
                                placeholder="Confirm your password"
                                value={confirmPassword}
                                onChange={(event) => setConfirmPassword(event.target.value)}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassConf((prev) => !prev)}
                                className={styles.showPassButton}
                            >
                                <img src={eyeIcon} alt="toggle" />
                            </button>
                        </div>
                        {error ? <div className={styles.errorMessage}>{error}</div> : null}
                        <button className={styles.submitButton} type="submit" disabled={isSubmitting}>
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