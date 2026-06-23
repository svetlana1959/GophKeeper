import Header from '../components/Header'
import styles from './Landing.module.css'
import Title from '../components/Title';
import icon1 from '../assets/Vector-3.png'
import icon2 from '../assets/Vector-1.png'
import icon3 from '../assets/Vector-2.png'
import icon4 from '../assets/Vector.png'
import safeIcon from '../assets/safe-icon.png'

function Landing() {
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
            <section className={styles.whyUs}>
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
        </>
    )
}

export default Landing;
