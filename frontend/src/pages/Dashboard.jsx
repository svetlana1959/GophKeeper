import styles from './Dashboard.module.css'
import reloadIcon from '../assets/qlementine-icons_update-16.svg'
import passwordIcon from '../assets/dashPass.svg'
import cardsIcon from '../assets/dashCard.svg'
import notesIcon from '../assets/dashNote.svg'
import filesIcon from '../assets/dashFiles.svg'
import laptopIcon from '../assets/laptopLightGreen.svg'
import mobileIcon from '../assets/mobileGreen.svg'
import windowsIcon from '../assets/windowsGreen.svg'
import { useState } from 'react'

function Dashboard() {
    const deviceTypeToIcon = {
        'laptop': laptopIcon,
        'mobile': mobileIcon,
        'windows': windowsIcon
    }

    const [devices, setDevices] = useState([
        {
            type: 'laptop',
            name: 'MacBook Pro',
            os: 'macOS 14.4',
            status: 'online'
        },
        {
            type: 'mobile',
            name: 'iPhone 17 Pro Max',
            os: 'iOS 26',
            status: 'online'
        },
        {
            type: 'windows',
            name: 'Windows PC',
            os: 'Windows 11',
            status: 'offline'
        }
    ])

    const [accessRequests, setAccessRequests] = useState([
        {
            type: 'laptop',
            name: 'New MacBook Air',
            os: 'macOS 14.5',
            timestamp: '2026-06-14T12:45:00Z'
        },
    ])

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
                            <table className={styles.deviceTable}>
                                {devices && devices.length > 0 ?
                                    devices.map((device, ind) =>
                                        <tr key={`trusted-devices-${ind}`} className={styles.deviceRow}>
                                            <td className={styles.deviceIcon}>
                                                <div className={styles.deviceIconBlock}>
                                                    <img src={deviceTypeToIcon[device.type]} alt="icon" />
                                                </div>
                                            </td>
                                            <td className={styles.deviceNames}>
                                                <div className={styles.deviceName}>{device.name}</div>
                                                <div className={styles.deviceOS}>{device.os}</div>
                                            </td>
                                            <td className={styles.deviceStatus}>
                                                {device.status === 'online' ? <span className={styles.deviceOnline}>Online</span> : <span className={styles.deviceOffline}>Offline</span>}
                                            </td>
                                        </tr>
                                    )
                                    :
                                    <div className={styles.emptyMessage}>No devices connected</div>
                                }
                            </table>
                            <div className={styles.addDevice}>
                                <button className={styles.addDeviceButton}>+ Add new device</button>
                            </div>
                        </div>
                        <div className={styles.block}>
                            <div className={styles.statusTitle}>
                                Security Status
                            </div>
                            <div className={styles.statusContainer}>
                                <div className={styles.statusIcon}>
                                    <svg width="13" height="16" viewBox="0 0 13 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M12 2.98389V7.52979C12 9.75372 10.6421 11.3743 9.19824 12.4692C8.48124 13.013 7.76077 13.4118 7.21875 13.6753C6.94843 13.8067 6.7237 13.9039 6.56836 13.9673C6.54396 13.9772 6.52087 13.9853 6.5 13.9937C6.47913 13.9853 6.45604 13.9772 6.43164 13.9673C6.2763 13.9039 6.05157 13.8067 5.78125 13.6753C5.23923 13.4118 4.51876 13.013 3.80176 12.4692C2.3579 11.3743 1 9.75372 1 7.52979V2.98389L6.5 1.05908L12 2.98389Z" stroke="#008645" />
                                        <path d="M0.5 2.62979V7.52979C0.5 12.4298 6.5 14.5298 6.5 14.5298C6.5 14.5298 12.5 12.4298 12.5 7.52979V2.62979L6.5 0.529785L0.5 2.62979Z" stroke="#008645" stroke-linecap="square" />
                                        <path d="M3.94922 6.9778L5.83389 8.86313L9.60522 5.0918" stroke="#23bd21" stroke-linecap="square" />
                                    </svg>
                                </div>
                                <div className={styles.statusContent}>
                                    <div className={styles.statusBlock}>
                                        <div className={styles.statusBlockIcon}>
                                            <svg width="13" height="16" viewBox="0 0 13 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path d="M12 2.98389V7.52979C12 9.75372 10.6421 11.3743 9.19824 12.4692C8.48124 13.013 7.76077 13.4118 7.21875 13.6753C6.94843 13.8067 6.7237 13.9039 6.56836 13.9673C6.54396 13.9772 6.52087 13.9853 6.5 13.9937C6.47913 13.9853 6.45604 13.9772 6.43164 13.9673C6.2763 13.9039 6.05157 13.8067 5.78125 13.6753C5.23923 13.4118 4.51876 13.013 3.80176 12.4692C2.3579 11.3743 1 9.75372 1 7.52979V2.98389L6.5 1.05908L12 2.98389Z" stroke="#008645" />
                                                <path d="M0.5 2.62979V7.52979C0.5 12.4298 6.5 14.5298 6.5 14.5298C6.5 14.5298 12.5 12.4298 12.5 7.52979V2.62979L6.5 0.529785L0.5 2.62979Z" stroke="#008645" stroke-linecap="square" />
                                                <path d="M3.94922 6.9778L5.83389 8.86313L9.60522 5.0918" stroke="#23bd21" stroke-linecap="square" />
                                            </svg>
                                        </div>
                                        <div className={styles.statusBlockContent}>
                                            <div className={styles.statusBlockTitle}>4 trusted devices</div>
                                            <div className={styles.statusBlockSubtitle}>Your devices are secure </div>
                                        </div>
                                    </div>
                                    <div className={styles.statusBlock}>
                                        <div className={styles.statusBlockIcon}>
                                            <svg width="13" height="16" viewBox="0 0 13 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path d="M12 2.98389V7.52979C12 9.75372 10.6421 11.3743 9.19824 12.4692C8.48124 13.013 7.76077 13.4118 7.21875 13.6753C6.94843 13.8067 6.7237 13.9039 6.56836 13.9673C6.54396 13.9772 6.52087 13.9853 6.5 13.9937C6.47913 13.9853 6.45604 13.9772 6.43164 13.9673C6.2763 13.9039 6.05157 13.8067 5.78125 13.6753C5.23923 13.4118 4.51876 13.013 3.80176 12.4692C2.3579 11.3743 1 9.75372 1 7.52979V2.98389L6.5 1.05908L12 2.98389Z" stroke="#008645" />
                                                <path d="M0.5 2.62979V7.52979C0.5 12.4298 6.5 14.5298 6.5 14.5298C6.5 14.5298 12.5 12.4298 12.5 7.52979V2.62979L6.5 0.529785L0.5 2.62979Z" stroke="#008645" stroke-linecap="square" />
                                                <path d="M3.94922 6.9778L5.83389 8.86313L9.60522 5.0918" stroke="#23bd21" stroke-linecap="square" />
                                            </svg>
                                        </div>
                                        <div className={styles.statusBlockContent}>
                                            <div className={styles.statusBlockTitle}>No security alerts </div>
                                            <div className={styles.statusBlockSubtitle}>Everything looks good </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className={styles.rightContent}>
                        <div className={styles.block}>
                            <div className={styles.blockTitle}>
                                <div className={styles.blockTitleText}>Pending Access Requests</div>
                                <button className={styles.blockTitleButton}>View All</button>
                            </div>
                            <div className={styles.accessRequests}>
                                {accessRequests && accessRequests.length > 0 ?
                                    accessRequests.map((request, ind) =>
                                        <div key={`access-request-${ind}`} className={styles.accessRequest}>
                                            <div className={styles.accessRequestInfo}>
                                                <div className={styles.accessRequestIcon}>
                                                    <img src={deviceTypeToIcon[request.type]} alt="icon" />
                                                </div>
                                                <div className={styles.accessRequestNames}>
                                                    <div className={styles.accessRequestName}>{request.name}</div>
                                                    <div className={styles.accessRequestOS}>{request.os}</div>
                                                </div>
                                                <div className={styles.accessRequestTime}>
                                                    {new Date(request.timestamp).toLocaleString()}
                                                </div>
                                            </div>

                                            <div className={styles.accessRequestActionsBlock}>
                                                <div className={styles.accessRequestIcon} style={{ opacity: 0 }}>
                                                    <img src={deviceTypeToIcon[request.type]} alt="icon" />
                                                </div>
                                                <div className={styles.accessRequestActions}>
                                                    <button className={`${styles.accessRequestAction} ${styles.approveButton}`}>Approve</button>
                                                    <button className={`${styles.accessRequestAction} ${styles.rejectButton}`}>Reject</button>
                                                </div>
                                                <div className={styles.accessRequestTime} style={{ opacity: 0 }}>
                                                    {new Date(request.timestamp).toLocaleString()}
                                                </div>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className={styles.emptyMessage}>No pending access requests</div>
                                    )}
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