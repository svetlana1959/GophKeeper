import { useState } from 'react'
import styles from './MainPage.module.css'
import logo from '../assets/logo.png'
import notificationIcon from '../assets/clarity_notification-line.svg'
import Dashboard from './Dashboard';

function MainPage({ linkPage }) {

    const [page, setPage] = useState(linkPage || 'dashboard');

    const pages = {
        'dashboard': <Dashboard />,
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
                    <div className={`${styles.navItem} ${page === 'dashboard' ? styles.active : ''}`} onClick={() => setPage('dashboard')}>Dashboard</div>
                    <div className={`${styles.navItem} ${page === 'secrets' ? styles.active : ''}`} onClick={() => setPage('secrets')}>Secrets</div>
                    <div className={`${styles.navItem} ${page === 'devices' ? styles.active : ''}`} onClick={() => setPage('devices')}>Devices</div>
                    <div className={`${styles.navItem} ${page === 'statistics' ? styles.active : ''}`} onClick={() => setPage('statistics')}>Statistics</div>
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