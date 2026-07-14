import { useNavigate } from 'react-router-dom'
import styles from './Logout.module.css'
import logo from '../assets/logo.png'
import { clearToken, getToken } from '../api/client'

function Logout() {
    const navigate = useNavigate()
    const isAuthed = Boolean(getToken())

    const handleLogout = () => {
        clearToken()
        navigate('/auth', { replace: true })
    }

    return (
        <div className={styles.page}>
            <div className={styles.card}>
                <div className={styles.brand}>
                    <img src={logo} alt="GophKeeper Logo" className={styles.logo} />
                    <div>
                        <div className={styles.title}>GophKeeper</div>
                        <div className={styles.subtitle}>Session control</div>
                    </div>
                </div>
                <h1 className={styles.heading}>{isAuthed ? 'You are signed in' : 'No active session'}</h1>
                <p className={styles.text}>
                    {isAuthed
                        ? 'Log out to switch accounts or create a new one.'
                        : 'You can sign in or register a new account.'}
                </p>
                {isAuthed ? (
                    <button className={styles.button} onClick={handleLogout}>Log out</button>
                ) : (
                    <button className={styles.button} onClick={() => navigate('/auth', { replace: true })}>Go to login</button>
                )}
            </div>
        </div>
    )
}

export default Logout