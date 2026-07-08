import styles from './Registration.module.css'
import logo from '../assets/logo.png'
import { Link } from 'react-router-dom'
import regLogo from '../assets/authLogo.svg'

function Authorization() {
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
                    <div className={styles.title}>Create your account</div>
                    <div className={styles.subtitle}>Join GophKeeper and keep your data secure.</div>
                    <form action="">
                        <label htmlFor="input">Username</label>
                        <input className={`${styles.input} ${styles.userInput}`} name='username' placeholder='Enter your username' />
                        <label htmlFor="input">Password</label>
                        <dir className={styles.inputWrapper}>
                            <input className={`${styles.input} ${styles.passInput}`} name='password' type='password' placeholder='Enter your password' />
                        </dir>
                        <button className={styles.submitButton} style={{ marginTop: "64px" }}>Log in</button>
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