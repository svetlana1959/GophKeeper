import React from 'react'
import styles from './Registration.module.css'
import background from '../assets/backgroundReg.png'
import secureLogo from '../assets/mingcute_safe-lock-line.svg'
import { Link } from 'react-router-dom'
import regLogo from '../assets/mdi_account-box-plus-outline.svg'

function Registration() {
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
                    <form action="">
                        <label htmlFor="name">Full name</label>
                        <input className={`${styles.input} ${styles.userInput}`} name='name' placeholder='Enter your full name' />
                        <label htmlFor="username">Username</label>
                        <input className={`${styles.input} ${styles.userInput}`} name='username' placeholder='Enter your username' />
                        <label htmlFor="password">Password</label>
                        <input className={`${styles.input} ${styles.passInput}`} name='password' placeholder='Create a strong password' />
                        <label htmlFor="confPass">Confirm password</label>
                        <input className={`${styles.input} ${styles.passInput}`} name='confPass' placeholder='Confirm your password' />
                        <button className={styles.submitButton}>Create account</button>
                    </form>
                    <div className={styles.hr}>
                        <div className={styles.hrLine}></div>
                        <div className={styles.hrText}>or</div>
                        <div className={styles.hrLine}></div>
                    </div>
                    <div className={styles.footer}>
                        Already have account? <Link to='/auth'>Log in</Link>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Registration;