import styles from './Dashboard.module.css'
import reloadIcon from '../assets/qlementine-icons_update-16.svg'
import passwordIcon from '../assets/dashPass.svg'
import cardsIcon from '../assets/dashCard.svg'
import notesIcon from '../assets/dashNote.svg'
import filesIcon from '../assets/dashFiles.svg'

function Dashboard() {
    return (
        <>
            <div className={styles.header}>
                <div className={styles.title}>Welcome to the Dashboard</div>
                <div className={styles.subtitle}>Here what's happening with your vault</div>
            </div>
            <div className={styles.content}>
                <div className={styles.sync}>
                    <button className={styles.syncButton}>
                        <img src={reloadIcon} alt="Reload" />
                    </button>
                    <div className={styles.syncStatus}>Last synced: <span className={styles.syncTimestamp}>14 June 2026, 12:43</span></div>
                </div>
                <div className={styles.cards}>
                    <div className={styles.card} style={{ backgroundColor: '#13181C' }}>
                        <div className={styles.cardIcon}>
                            <img src={passwordIcon} alt="Passwords" />
                        </div>
                        <div className={styles.cardContent}>
                            <div className={styles.cardTitle}>Passwords</div>
                            <div className={styles.cardNumber}>12</div>
                            <div className={styles.cardTitle}>Total</div>
                        </div>
                    </div>
                    <div className={styles.card}>
                        <div className={styles.cardIcon}>
                            <img src={cardsIcon} alt="Bank Cards" />
                        </div>
                        <div className={styles.cardContent}>
                            <div className={styles.cardTitle}>Bank Cards</div>
                            <div className={styles.cardNumber}>12</div>
                            <div className={styles.cardTitle}>Total</div>
                        </div>
                    </div>
                    <div className={styles.card}>
                        <div className={styles.cardIcon}>
                            <img src={notesIcon} alt="Notes" />
                        </div>
                        <div className={styles.cardContent}>
                            <div className={styles.cardTitle}>Notes</div>
                            <div className={styles.cardNumber}>12</div>
                            <div className={styles.cardTitle}>Total</div>
                        </div>
                    </div>
                    <div className={styles.card}>
                        <div className={styles.cardIcon}>
                            <img src={filesIcon} alt="Files" />
                        </div>
                        <div className={styles.cardContent}>
                            <div className={styles.cardTitle}>Files</div>
                            <div className={styles.cardNumber}>12</div>
                            <div className={styles.cardTitle}>Total</div>
                        </div>
                    </div>
                </div>
                <div className={styles.container}>
                    <div className={styles.leftContent}>
                        <div className={styles.block}>
                            <div className={styles.blockTitle}>
                                <div className={styles.blockTitleText}>Trusted Devices</div>
                                <button className={styles.blockTitleButton}>View All</button>
                            </div>
                        </div>
                        <div className={styles.block}>
                            
                        </div>
                    </div>
                    <div className={styles.rightContent}>
                        <div className={styles.block}>
                            <div className={styles.blockTitle}>
                                <div className={styles.blockTitleText}>Pending Access Requests</div>
                                <button className={styles.blockTitleButton}>View All</button>
                            </div>
                        </div>
                        <div className={styles.block}>
                            <div className={styles.blockTitle}>
                                <div className={styles.blockTitleText}>Recent Activity</div>
                                <button className={styles.blockTitleButton}>View All</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    )
}

export default Dashboard;