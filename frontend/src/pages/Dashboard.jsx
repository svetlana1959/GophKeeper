import styles from './Dashboard.module.css'
import reloadIcon from '../assets/qlementine-icons_update-16.svg'
import passwordIcon from '../assets/dashPass.svg'
import cardsIcon from '../assets/dashCard.svg'
import notesIcon from '../assets/dashNote.svg'
import filesIcon from '../assets/dashFiles.svg'
import laptopIcon from '../assets/laptopLightGreen.svg'
import mobileIcon from '../assets/mobileGreen.svg'
import windowsIcon from '../assets/windowsGreen.svg'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

function Dashboard({ account }) {
    const deviceTypeToIcon = {
        'laptop': laptopIcon,
        'mobile': mobileIcon,
        'windows': windowsIcon
    }

    const [period, setPeriod] = useState('7d')
    const [isLoading, setIsLoading] = useState(true)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [error, setError] = useState('')
    const [overview, setOverview] = useState(null)
    const [security, setSecurity] = useState(null)
    const [activityPoints, setActivityPoints] = useState([])
    const [devices, setDevices] = useState([])
    const [lastSyncedAt, setLastSyncedAt] = useState('')
    const [invite, setInvite] = useState({ isSubmitting: false, error: '', code: '', expiresAt: '' })
    const [optionalApiStatus, setOptionalApiStatus] = useState({ health: 'n/a', whoami: 'n/a', changes: 'n/a' })

    const inferDeviceType = (name = '') => {
        const lower = name.toLowerCase()
        if (lower.includes('iphone') || lower.includes('android') || lower.includes('mobile') || lower.includes('phone')) {
            return 'mobile'
        }
        if (lower.includes('windows') || lower.includes('win')) {
            return 'windows'
        }
        return 'laptop'
    }

    const resolvePresence = (device) => {
        if (device.status !== 'active') {
            return 'offline'
        }

        if (!device.last_seen_at) {
            return 'offline'
        }

        const lastSeen = new Date(device.last_seen_at).getTime()
        const tenMinutesMs = 10 * 60 * 1000
        return Date.now() - lastSeen <= tenMinutesMs ? 'online' : 'offline'
    }

    const normalizedDevices = useMemo(() => {
        return devices.map((device) => ({
            ...device,
            type: inferDeviceType(device.device_name),
            name: device.device_name,
            os: device.status,
            status: resolvePresence(device),
        }))
    }, [devices])

    const accessRequests = useMemo(() => {
        return devices
            .filter((device) => device.status === 'pending')
            .map((device) => ({
                id: device.id,
                type: inferDeviceType(device.device_name),
                name: device.device_name,
                os: device.status,
                timestamp: device.updated_at,
            }))
    }, [devices])

    const loadData = useCallback(async ({ keepSpinner = false } = {}) => {
        if (keepSpinner) {
            setIsRefreshing(true)
        } else {
            setIsLoading(true)
        }

        setError('')

        const [
            overviewResult,
            securityResult,
            activityResult,
            devicesResult,
            meResult,
            healthResult,
            whoamiResult,
            changesResult,
        ] = await Promise.allSettled([
            api.statsOverview(),
            api.statsSecurity(),
            api.statsActivity(period),
            api.listDevices(),
            api.me(),
            api.health(),
            api.whoami(),
            api.syncChanges(0),
        ])

        if (overviewResult.status === 'fulfilled') {
            setOverview(overviewResult.value)
        }

        if (securityResult.status === 'fulfilled') {
            setSecurity(securityResult.value)
        }

        if (activityResult.status === 'fulfilled') {
            setActivityPoints(activityResult.value.points ?? [])
        }

        if (devicesResult.status === 'fulfilled') {
            setDevices(devicesResult.value ?? [])
        }

        if (meResult.status === 'fulfilled' && !account) {
            // Keep account endpoint connected even when MainPage already loaded it.
        }

        const nextOptionalStatus = {
            health: healthResult.status === 'fulfilled' ? (healthResult.value.status ?? 'ok') : 'unavailable',
            whoami: whoamiResult.status === 'fulfilled' ? 'ok' : 'unavailable',
            changes: changesResult.status === 'fulfilled' ? 'ok' : 'unavailable',
        }
        setOptionalApiStatus(nextOptionalStatus)

        if (changesResult.status === 'fulfilled') {
            const cursor = changesResult.value.cursor
            setLastSyncedAt(`cursor ${cursor}`)
        } else if (securityResult.status === 'fulfilled') {
            setLastSyncedAt(new Date(securityResult.value.last_sync_at).toLocaleString())
        } else {
            setLastSyncedAt('never')
        }

        const hardFailures = [overviewResult, securityResult, activityResult, devicesResult].every((result) => result.status === 'rejected')
        if (hardFailures) {
            setError('Failed to load dashboard data. Please refresh.')
        }

        setIsLoading(false)
        setIsRefreshing(false)
    }, [account, period])

    useEffect(() => {
        loadData()
    }, [loadData])

    const handleCreateInvite = async () => {
        setInvite((prev) => ({ ...prev, isSubmitting: true, error: '' }))

        try {
            const response = await api.createInvite()
            setInvite({
                isSubmitting: false,
                error: '',
                code: response.code,
                expiresAt: response.expires_at,
            })
        } catch (err) {
            setInvite((prev) => ({
                ...prev,
                isSubmitting: false,
                error: err.message || 'Failed to create invite',
            }))
        }
    }

    const renderCardValue = (value) => (typeof value === 'number' ? value : '-')

    if (isLoading) {
        return (
            <>
                <div className={styles.header}>
                    <div className={styles.title}>Welcome to the Dashboard</div>
                    <div className={styles.subtitle}>Loading data from API...</div>
                </div>
            </>
        )
    }

    return (
        <>
            <div className={styles.header}>
                <div className={styles.title}>Welcome to the Dashboard</div>
                <div className={styles.subtitle}>Here what's happening with your vault</div>
            </div>
            <div className={styles.content}>
                <div className={styles.sync}>
                    <button className={styles.syncButton} onClick={() => loadData({ keepSpinner: true })} disabled={isRefreshing}>
                        <img src={reloadIcon} alt="Reload" />
                    </button>
                    <div className={styles.syncStatus}>Last synced: <span className={styles.syncTimestamp}>{lastSyncedAt || 'never'}</span></div>
                </div>
                {error ? <div className={styles.emptyMessage}>{error}</div> : null}
                <div className={styles.cards}>
                    <div className={styles.card} style={{ backgroundColor: '#13181C' }}>
                        <div className={styles.cardIcon}>
                            <img src={passwordIcon} alt="Passwords" />
                        </div>
                        <div className={styles.cardContent}>
                            <div className={styles.cardTitle}>Passwords</div>
                            <div className={styles.cardNumber}>{renderCardValue(overview?.passwords)}</div>
                            <div className={styles.cardTitle}>Total</div>
                        </div>
                    </div>
                    <div className={styles.card}>
                        <div className={styles.cardIcon}>
                            <img src={cardsIcon} alt="Bank Cards" />
                        </div>
                        <div className={styles.cardContent}>
                            <div className={styles.cardTitle}>Bank Cards</div>
                            <div className={styles.cardNumber}>{renderCardValue(overview?.bank_cards)}</div>
                            <div className={styles.cardTitle}>Total</div>
                        </div>
                    </div>
                    <div className={styles.card}>
                        <div className={styles.cardIcon}>
                            <img src={notesIcon} alt="Notes" />
                        </div>
                        <div className={styles.cardContent}>
                            <div className={styles.cardTitle}>Notes</div>
                            <div className={styles.cardNumber}>{renderCardValue(overview?.notes)}</div>
                            <div className={styles.cardTitle}>Total</div>
                        </div>
                    </div>
                    <div className={styles.card}>
                        <div className={styles.cardIcon}>
                            <img src={filesIcon} alt="Files" />
                        </div>
                        <div className={styles.cardContent}>
                            <div className={styles.cardTitle}>Files</div>
                            <div className={styles.cardNumber}>{renderCardValue(overview?.files)}</div>
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
                                {normalizedDevices && normalizedDevices.length > 0 ?
                                    normalizedDevices.map((device, ind) =>
                                        <tr key={`trusted-devices-${ind}`} className={styles.deviceRow}>
                                            <td className={styles.deviceIcon}>
                                                <div className={styles.deviceIconBlock}>
                                                    <img src={deviceTypeToIcon[device.type] ?? laptopIcon} alt="icon" />
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
                                <button className={styles.addDeviceButton} onClick={handleCreateInvite} disabled={invite.isSubmitting}>
                                    {invite.isSubmitting ? 'Creating invite...' : '+ Add new device'}
                                </button>
                                {invite.code ? (
                                    <div className={styles.emptyMessage}>
                                        Invite code: {invite.code} (expires {new Date(invite.expiresAt).toLocaleString()})
                                    </div>
                                ) : null}
                                {invite.error ? <div className={styles.emptyMessage}>{invite.error}</div> : null}
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
                                            <div className={styles.statusBlockTitle}>{renderCardValue(security?.trusted_devices)} trusted devices</div>
                                            <div className={styles.statusBlockSubtitle}>Health: {optionalApiStatus.health}</div>
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
                                            <div className={styles.statusBlockTitle}>{renderCardValue(security?.alerts)} security alerts</div>
                                            <div className={styles.statusBlockSubtitle}>Session check: {optionalApiStatus.whoami}</div>
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
                                                    <img src={deviceTypeToIcon[request.type] ?? laptopIcon} alt="icon" />
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
                                                    <img src={deviceTypeToIcon[request.type] ?? laptopIcon} alt="icon" />
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
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                    <button className={styles.blockTitleButton} onClick={() => setPeriod('7d')}>7d</button>
                                    <button className={styles.blockTitleButton} onClick={() => setPeriod('30d')}>30d</button>
                                    <button className={styles.blockTitleButton} onClick={() => setPeriod('90d')}>90d</button>
                                </div>
                            </div>
                            <div className={styles.accessRequests}>
                                {activityPoints.length > 0 ? activityPoints.slice(-5).map((point) => (
                                    <div key={point.date} className={styles.accessRequest}>
                                        <div className={styles.accessRequestInfo}>
                                            <div className={styles.accessRequestNames}>
                                                <div className={styles.accessRequestName}>{point.date}</div>
                                                <div className={styles.accessRequestOS}>
                                                    created: {point.created}, updated: {point.updated}, deleted: {point.deleted}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )) : <div className={styles.emptyMessage}>No activity for period {period}</div>}
                                <div className={styles.emptyMessage}>changes endpoint: {optionalApiStatus.changes}</div>
                                <div className={styles.emptyMessage}>account: {account?.id ?? 'unknown'}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    )
}

export default Dashboard;