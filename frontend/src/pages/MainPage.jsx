import { useState } from 'react'
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

function MainPage({ linkPage }) {

    const [page, setPage] = useState(linkPage || 'dashboard');

    const pages = {
        'dashboard': <Dashboard />,
    }

    const navigate = useNavigate();

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
                </div>
                <div className={styles.account}>
                    <div className={styles.accountIcon}>S</div>
                    <div className={styles.accountInfo}>
                        <div className={styles.accountName}>Sergey</div>
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