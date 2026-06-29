import { useRef, useState } from 'react';
import Header from '../components/Header'
import styles from './Landing.module.css'
import Title from '../components/Title';
import icon1 from '../assets/Vector-3.png'
import icon2 from '../assets/Vector-1.png'
import icon3 from '../assets/Vector-2.png'
import icon4 from '../assets/Vector.png'
import icon5 from '../assets/hiw1.png'
import icon6 from '../assets/hiw3.png'
import icon7 from '../assets/hiw2.png'
import icon8 from '../assets/hiw4.png'
import copyButton from '../assets/copyButton.png'
import checkIcon from '../assets/copied.svg'
import safeIcon from '../assets/safe-icon.png'
import searchIcon from '../assets/material-symbols_search.png'
import bankCardIcon from '../assets/bankCardType.png'
import fileIcon from '../assets/fileType.png'
import passwordIcon from '../assets/passwordType.svg'
import laptopIcon from '../assets/laptop.png'
import laptopGreenIcon from '../assets/laptopGreen.svg'
import mobileIcon from '../assets/mobile.png'
import windowsIcon from '../assets/windows.png'
import verifIcon from '../assets/verif.svg'

function Landing() {
    const terminalRef = useRef(null);
    const [isCopied, setIsCopied] = useState(false);

    const handleCopy = async () => {
        console.log("ded")
        if (!terminalRef.current) return;

        const textToCopy = terminalRef.current.innerText.trim();

        try {
            await navigator.clipboard.writeText(textToCopy);
            setIsCopied(true);

            // Возвращаем исходную иконку через 2 секунды
            setTimeout(() => {
                setIsCopied(false);
            }, 2000);
        } catch (err) {
            console.error('Не удалось скопировать текст: ', err);
        }
    };

    const [secrets, _] = useState([
        {
            type: 'password',
            name: 'GitHub',
            lastUpdated: 'Today, 12:45',
            deviceAccess: ['laptop', 'mobile', 'windows'],
        },
        {
            type: 'password',
            name: 'Gmail',
            lastUpdated: 'Yesterday, 10:13',
            deviceAccess: ['laptop', 'mobile'],
        },
        {
            type: 'bankCard',
            name: 'Mir',
            lastUpdated: '3 days ago',
            deviceAccess: ['mobile'],
        },
        {
            type: 'file',
            name: 'Passport scan.pdf',
            lastUpdated: '1 week ago',
            deviceAccess: ['laptop'],
        },
    ]);

    const secretTypeToNameTextMap = {
        'password': 'Password',
        'bankCard': 'Bank Cards',
        'file': 'File'
    }

    const deviceTypeToIcon = {
        'laptop': laptopIcon,
        'mobile': mobileIcon,
        'windows': windowsIcon
    }

    function passwordElement() {
        return (
            <div className={styles.builtSecretsListTableType}
                style={{
                    background: "#103C23",
                }}
            >
                <img src={passwordIcon} />
            </div>
        )
    }

    function bankCardElement() {
        return (
            <div className={styles.builtSecretsListTableType}
                style={{
                    background: "#2C2504",
                }}
            >
                <img src={bankCardIcon} />
            </div>
        )
    }

    function fileElement() {
        return (
            <div className={styles.builtSecretsListTableType}
                style={{
                    background: "#103C23",
                }}
            >
                <img src={fileIcon} />
            </div>
        )
    }


    const secretTypeToIcon = {
        'password': passwordElement,
        'bankCard': bankCardElement,
        'file': fileElement
    }

    return (
        <>
            <Header />
            <section className={styles.hero}>
                <div className={styles.heroContent}>
                    <div>
                        <Title style={{ fontSize: "102px", fontWeight: "600" }} styleBlock={{ marginLeft: "-8px" }} />
                        <span className={styles.heroSubtitle}>Distributed Secret Management</span>
                        <p className={styles.heroDescription}>Store, sync and manage secrets across trusted devices.</p>
                    </div>
                    <div className={styles.heroAction}>
                        <button className={styles.heroButton}>Get Started</button>
                        <button className={styles.heroButtonOutline}>View Documentation</button>
                    </div>
                </div>
                <div className={styles.heroImage}></div>
            </section>
            <section className={styles.whyUs} id='features'>
                <div className={styles.whyUsTitle}>Why <Title /></div>
                <p className={styles.whyUsSubtitle}>
                    GophKeeper gives you powerful encryption and seamless <br />
                    control over your secrets, so you can build and operate with total confidence.
                </p>
                <div className={styles.whyUsContainer}>
                    <div className={styles.whyUsContainerChild}>
                        <div className={styles.whyUsIcon}>
                            <img src={icon1} alt="Zero-knowledge encryption icon" />
                        </div>
                        <div className={styles.whyUsContainerChildTitle}>
                            Zero-Knowledge Encryption
                        </div>
                        <div className={styles.whyUsContainerChildSubtitle}>
                            Secrets are encrypted on the client side before they leave your device. Only you can decrypt them.
                        </div>
                        <div className={styles.whyUsContainerChildFooterHelper}></div>
                        <div className={styles.whyUsContainerChildFooter}>
                            <div className={styles.whyUsContainerChildFooterHr}></div>
                            <div className={styles.whyUsContainerChildFooterContent}>
                                <img src={safeIcon} alt="Security shield icon" />
                                <p>Your secrets stay yours</p>
                            </div>
                        </div>
                    </div>
                    <div className={styles.whyUsContainerChild}>
                        <div className={styles.whyUsIcon}>
                            <img src={icon2} alt="CLI-focused features icon" />
                        </div>
                        <div className={styles.whyUsContainerChildTitle}>
                            CLI First
                        </div>
                        <div className={styles.whyUsContainerChildSubtitle}>
                            Built for developers who works in the terminal. Powerful CLI for everyday secret management.
                        </div>
                        <div className={styles.whyUsContainerChildFooterHelper}></div>
                        <div className={styles.whyUsContainerChildFooter}>
                            <div className={styles.whyUsContainerChildFooterHr}></div>
                            <div className={styles.whyUsContainerChildFooterContent}>
                                <img src={safeIcon} alt="Security shield icon" />
                                <p>Fast. Powerful. Developer-friendly</p>
                            </div>
                        </div>
                    </div>
                    <div className={styles.whyUsContainerChild}>
                        <div className={styles.whyUsIcon}>
                            <img src={icon3} alt="Synchronization icon" />
                        </div>
                        <div className={styles.whyUsContainerChildTitle}>
                            Distributed Synchronization
                        </div>
                        <div className={styles.whyUsContainerChildSubtitle}>
                            Access the same secrets securely across all your trusted devices.
                        </div>
                        <div className={styles.whyUsContainerChildFooterHelper}></div>
                        <div className={styles.whyUsContainerChildFooter}>
                            <div className={styles.whyUsContainerChildFooterHr}></div>
                            <div className={styles.whyUsContainerChildFooterContent}>
                                <img src={safeIcon} alt="Security shield icon" />
                                <p>Sync anywhere, securely</p>
                            </div>
                        </div>
                    </div>
                    <div className={styles.whyUsContainerChild}>
                        <div className={styles.whyUsIcon}>
                            <img src={icon4} alt="Trusted devices icon" />
                        </div>
                        <div className={styles.whyUsContainerChildTitle}>
                            Trusted Devices
                        </div>
                        <div className={styles.whyUsContainerChildSubtitle}>
                            You control which devices can access your secrets through a secure trust chain.
                        </div>
                        <div className={styles.whyUsContainerChildFooterHelper}></div>
                        <div className={styles.whyUsContainerChildFooter}>
                            <div className={styles.whyUsContainerChildFooterHr}></div>
                            <div className={styles.whyUsContainerChildFooterContent}>
                                <img src={safeIcon} alt="Security shield icon" />
                                <p>Full access control</p>
                            </div>
                        </div>
                    </div>
                </div>
                <div className={styles.whyUsFooter}>
                    <div className={styles.whyUsFooterIcon}>
                        <img src={safeIcon} alt="Security shield icon" />
                    </div>
                    <div className={styles.whyUsFooterContainer}>
                        <div className={styles.whyUsFooterContent}>Secure</div>
                        <div className={styles.whyUsFooterContent}>Privacy by default</div>
                        <div className={styles.whyUsFooterContent}>End-to-end encryption</div>
                    </div>
                </div>
            </section>
            <section className={styles.howItWorks} id='howItWorks'>
                <div className={styles.howItWorksTitle}>How It <span style={{ color: "#008645" }}>Works</span></div>
                <p className={styles.howItWorksSubtitle}>
                    Simple. Secure. Distributed.
                </p>
                <div className={styles.howItWorksContainer}>
                    <div className={styles.howItWorksContainerChildren}>
                        <div className={styles.howItWorksContainerChildrenMain}>
                            <div className={styles.howItWorksContainerChildrenMainNumber}>
                                1
                            </div>
                            <div className={styles.howItWorksContainerChildrenMainIcon}
                                style={{ backgroundImage: `url(${icon5})` }}></div>
                        </div>
                        <div className={styles.howItWorksContainerChildrenTitle}>
                            Create a secret
                        </div>
                        <div className={styles.howItWorksContainerChildrenSubtitle}>
                            Add your secret using CLI or the app. It’s encrypted on your device.
                        </div>
                    </div>
                    <div className={styles.howItWorksContainerChildren}>
                        <div className={styles.howItWorksContainerChildrenMain}>
                            <div className={styles.howItWorksContainerChildrenMainNumber}>
                                2
                            </div>
                            <div className={styles.howItWorksContainerChildrenMainIcon}
                                style={{ backgroundImage: `url(${icon6})` }}></div>
                        </div>
                        <div className={styles.howItWorksContainerChildrenTitle}>
                            Sync securely
                        </div>
                        <div className={styles.howItWorksContainerChildrenSubtitle}>
                            Your secret is encrypted and synced to the network. We never see your data
                        </div>
                    </div>
                    <div className={styles.howItWorksContainerChildren}>
                        <div className={styles.howItWorksContainerChildrenMain}>
                            <div className={styles.howItWorksContainerChildrenMainNumber}>
                                3
                            </div>
                            <div className={styles.howItWorksContainerChildrenMainIcon}
                                style={{ backgroundImage: `url(${icon7})` }}></div>
                        </div>
                        <div className={styles.howItWorksContainerChildrenTitle}>
                            Access anywhere
                        </div>
                        <div className={styles.howItWorksContainerChildrenSubtitle}>
                            Access your secrets from any trusted device in your trust chain.
                        </div>
                    </div>
                    <div className={styles.howItWorksContainerChildren}>
                        <div className={styles.howItWorksContainerChildrenMain}>
                            <div className={styles.howItWorksContainerChildrenMainNumber}>
                                4
                            </div>
                            <div className={styles.howItWorksContainerChildrenMainIcon}
                                style={{ backgroundImage: `url(${icon8})` }}></div>
                        </div>
                        <div className={styles.howItWorksContainerChildrenTitle}>
                            You’re in control
                        </div>
                        <div className={styles.howItWorksContainerChildrenSubtitle}>
                            Manage devices, permissions and revoke access at any time.
                        </div>
                    </div>
                </div>
            </section>
            <section className={styles.built} id='getStarted'>
                <div className={styles.builtLeftBlock}>
                    <div>
                        <div className={styles.builtTitle}>Built for <span style={{ color: "#008645" }}>developers</span></div>
                        <div className={styles.builtSubtitle}>Everything you need in terminal.</div>
                    </div>
                    <div className={styles.builtTerminal} ref={terminalRef}>
                        <span className={styles.builtTerminalComment}># Install GophKeeper</span>
                        <span className={styles.builtTerminalCode}>$ gopher install</span>
                        <span className={styles.builtTerminalComment}># Add a secret</span>
                        <span className={styles.builtTerminalCode}>$ gopher secret set database/passwords</span>
                        <span className={styles.builtTerminalComment}># View your secrets</span>
                        <span className={styles.builtTerminalCode}>$ gopher secret list</span>
                        <span className={styles.builtTerminalComment}># Sync across devices</span>
                        <span className={styles.builtTerminalCode}>$ gopher sync</span>

                        <button className={styles.builtTerminalCopyButton}
                            onClick={handleCopy}
                        ><img src={isCopied ? checkIcon : copyButton} alt="" /></button>
                    </div>
                </div>
                <div className={styles.builtRightBlock}>
                    <div className={styles.builtSecretsList}>
                        <div className={styles.builtSecretsListTitle}>Secrets</div>
                        <div className={styles.builtSecretsListActionPanel}>
                            <input className={styles.builtSecretsListActionPanelInput}
                                style={{ backgroundImage: `url(${searchIcon})` }}
                                placeholder='Search secrets...' />
                            <button
                                className={styles.builtSecretsListActionPanelAddButton}
                            >
                                + New Secret
                            </button>
                        </div>
                        <div className={styles.builtSecretsListTableBlock}>
                            <table className={styles.builtSecretsListTable}>
                                <thead>
                                    <tr className={styles.builtSecretsListTableHeadTr}>
                                        <th className={styles.colType}>Type</th>
                                        <th className={styles.colName}>Name</th>
                                        <th className={styles.colLastUpdated}>Last Updated</th>
                                        <th className={styles.colDeviceAccess}>Device Access</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {secrets.map((secret, ind) => (
                                        <tr key={`table-row-${ind + 1}`} className={styles.builtSecretsListTableTr}>
                                            <td className={styles.colType}>
                                                <div className={`${styles.builtSecretsListTableType} ${styles[secret.type]}`}>
                                                    {secretTypeToIcon[secret.type]()}
                                                </div>
                                            </td>
                                            <td className={`${styles.colName} ${styles.builtSecretsListTableTdNameCell}`}>
                                                <span className={styles.builtSecretsListTableTdNameText}>{secret.name}</span>
                                                <span className={styles.builtSecretsListTableTdTypeText}>{secretTypeToNameTextMap[secret.type]}</span>
                                            </td>
                                            <td className={`${styles.colLastUpdated} ${styles.builtSecretsListTableTdContentLastUpdate}`}>
                                                {secret.lastUpdated}
                                            </td>
                                            <td className={`${styles.colDeviceAccess} ${styles.builtSecretsListTableTdContentDevices}`}>
                                                <div className={styles.deviceIconsGap}>
                                                    {secret.deviceAccess.map((deviceType, indx) => (
                                                        <img key={`row-${ind}-icon-${indx}`} src={deviceTypeToIcon[deviceType]} alt="" />
                                                    ))}
                                                </div>
                                                <span className={styles.deviceCountText}>
                                                    {secret.deviceAccess.length} {secret.deviceAccess.length === 1 ? 'device' : 'devices'}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div className={styles.builtSecret}>
                        <div className={styles.builtSecretHeader}>
                            <div className={styles.builtSecretIcon}>
                                <img src={passwordIcon} />
                            </div>

                            <div className={styles.builtSecretVerif}>
                                <img src={verifIcon} alt="icon" />
                            </div>
                        </div>
                        <div className={styles.builtSecretTitle}>Secret</div>
                        <div className={styles.builtSecretSubtitle}>Password</div>

                        <div className={styles.builtSecretDescription}>
                            <div className={styles.builtSecretDescriptionType}>
                                <div className={styles.builtSecretDescriptionLeft}>Type</div>
                                <div className={styles.builtSecretDescriptionRight}>Password</div>
                            </div>
                            <div className={styles.builtSecretDescriptionType}>
                                <div className={styles.builtSecretDescriptionLeft}>Created</div>
                                <div className={styles.builtSecretDescriptionRight}>12 June 2026, 10:22</div>
                            </div>
                            <div className={styles.builtSecretDescriptionType}>
                                <div className={styles.builtSecretDescriptionLeft}>Last Modified</div>
                                <div className={styles.builtSecretDescriptionRight}>Today, 12:45</div>
                            </div>
                        </div>

                        <div className={styles.builtSecretHr}></div>

                        <div className={styles.builtSecretDevices}>
                            <div className={styles.builtSecretDevicesTitle}>Devices with access</div>
                            <div className={styles.builtSecretDevicesContent}>
                                <div className={styles.builtSecretDevice}>
                                    <div className={styles.builtSecretDeviceIcon}>
                                        <img src={laptopGreenIcon} alt="Mac" />
                                    </div>
                                    <div className={styles.builtSecretDeviceNames}>
                                        <div className={styles.builtSecretDeviceName}>Macbook Pro</div>
                                        <div className={styles.builtSecretDeviceVersion}>macOS 14.4</div>
                                    </div>
                                </div>
                                <div className={styles.builtSecretDeviceStatus}>Online</div>
                            </div>
                        </div>

                        <div className={styles.builtSecretActionPanel}>
                            <button className={styles.builtSecretActionPanelButton}
                                style={{ background: "#008645" }}
                                onClick={() => alert("fdsfd")}
                            >
                                View Secret
                            </button>
                            <button className={styles.builtSecretActionPanelButton}
                                style={{ background: "#242424" }}
                            >
                                Share
                            </button>
                            <button className={styles.builtSecretActionPanelButton}
                                style={{ background: "#242424" }}
                            >
                                Edit
                            </button>
                            <button className={styles.builtSecretActionPanelButton}
                                style={{ background: "#690000" }}
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            </section>
            <section className={styles.getStarted}>
                <div className={styles.getStartedTitle}>Ready to take <span style={{color: "#008645"}}>control</span> of your secrets?</div>
                <div className={styles.getStartedSubtitle}>Join developers who trust GophKeeper for secure secret management.</div>
                <div className={styles.getStartedHr}></div>
                <div className={styles.getStartedActionPanel}>
                    <div className={styles.getStartedActionPanelStartButton}>Get Started</div>
                    <div className={styles.getStartedActionPanelGithubButton}>View on Github</div>
                </div>
            </section>
        </>
    )
}

export default Landing;
