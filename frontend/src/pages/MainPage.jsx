import { useEffect, useState } from 'react'
import styles from './MainPage.module.css'
import logo from '../assets/logo.png'
import notificationIcon from '../assets/clarity_notification-line.svg'
import Dashboard from './Dashboard';
import dashboardIcon from '../assets/dashboardIcon.svg'
import secretsIcon from '../assets/secretsIcon.svg'
import devicesIcon from '../assets/devicesIcon.svg'
import statisticsIcon from '../assets/statisticsIcon.svg'
import settingsIcon from '../assets/settingsIcon.svg'
import dashboardActiveIcon from '../assets/dashboardIconActive.svg'
import secretsActiveIcon from '../assets/secretsIconActive.svg'
import devicesActiveIcon from '../assets/devicesIconActive.svg'
import statisticsActiveIcon from '../assets/statisticsIconActive.svg'
import settingsActiveIcon from '../assets/settingsIconActive.svg'
import { useNavigate } from 'react-router-dom';
import { api, clearToken, getToken } from '../api/client';

function MainPage({ linkPage }) {

    const [page, setPage] = useState(linkPage || 'dashboard');
    const [isCheckingSession, setIsCheckingSession] = useState(true)
    const [account, setAccount] = useState(null)

    const pages = {
        'dashboard': <Dashboard account={account} />,
    }

    const navigate = useNavigate();

    useEffect(() => {
        let isMounted = true

        const verifySession = async () => {
            const token = getToken()
            if (!token) {
                navigate('/auth', { replace: true })
                return
            }

            try {
                const me = await api.me()
                if (isMounted) {
                    setAccount(me)
                }
            } catch {
                clearToken()
                if (isMounted) {
                    navigate('/auth', { replace: true })
                }
            } finally {
                if (isMounted) {
                    setIsCheckingSession(false)
                }
            }
        }

        verifySession()

        return () => {
            isMounted = false
        }
    }, [navigate])

    if (isCheckingSession) {
        return (
            <div className={styles.container}>
                <div className={styles.content}>
                    <div className={styles.placeholder}>Checking authorization...</div>
                </div>
            </div>
        )
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
                <div className={styles.navbar}>
                    <div className={`${styles.navItem} ${page === 'dashboard' ? styles.active : ''}`} onClick={() => setPage('dashboard')}>
                        <img src={page === 'dashboard' ? dashboardActiveIcon : dashboardIcon} alt="Dashboard" />
                        Dashboard
                    </div>
                    <div className={`${styles.navItem} ${page === 'secrets' ? styles.active : ''}`} onClick={() => setPage('secrets')}>
                        <img src={page === 'secrets' ? secretsActiveIcon : secretsIcon} alt="Secrets" />
                        Secrets
                    </div>
                    <div className={`${styles.navItem} ${page === 'devices' ? styles.active : ''}`} onClick={() => setPage('devices')}>
                        <img src={page === 'devices' ? devicesActiveIcon : devicesIcon} alt="Devices" />
                        Devices
                    </div>
                    <div className={`${styles.navItem} ${page === 'statistics' ? styles.active : ''}`} onClick={() => setPage('statistics')}>
                        <img src={page === 'statistics' ? statisticsActiveIcon : statisticsIcon} alt="Statistics" />
                        Statistics
                    </div>
                    <div className={`${styles.navItem} ${page === 'settings' ? styles.active : ''}`} onClick={() => setPage('settings')}>
                        <img src={page === 'settings' ? settingsActiveIcon : settingsIcon} alt="Settings" />
                        Settings
                    </div>
                </div>
                <div className={styles.account}>
                    <div className={styles.accountIcon}>S</div>
                    <div className={styles.accountInfo}>
                        <div className={styles.accountName}>Account {account?.id?.slice(0, 8) ?? 'User'}</div>
                        <div className={styles.accountType}>Personal account</div>
                    </div>
                    <div className={styles.accountSettings} onClick={() => navigate('/logout', { replace: false })}>
                        Logout
                    </div>
                </div>
            </div>
            <div className={styles.content}>
                <div className={styles.contentHeader}>
                    <button className={styles.notifications}>
                        <img src={notificationIcon} alt="Notifications" />
                    </button>
                    <div className={styles.userIcon}>S</div>
                </div>
                {pages[page] ?? <div className={styles.placeholder}>We are sorry page "{page}" is in progress</div>}
            </div>
        </div>
    )
}

export default MainPage;