import React from 'react'
import Header from '../components/Header'
import styles from './Landing.module.css'
import Title from '../components/Title';

function Landing() {
    return (
        <>
            <Header />
            <section className={styles.hero}>
                <div className={styles.heroContent}>
                    <div>
                        <Title style={{ fontSize: "102px", fontWeight: "600"}} styleBlock={{ marginLeft: "-8px" }}/>
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
        </>
    )
}

export default Landing;
