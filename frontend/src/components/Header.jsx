import React from 'react'
import styles from './Header.module.css'
import logo from '../assets/logo.png'
import Title from './Title';

function Header() {
  return (
    <header className={styles.header}>
        <div className={styles.logo}>
            <img src={logo} alt="GophKeeper Logo" className={styles.logoImage} />
            <Title style={{fontSize: "32px", fontWeight: "400"}} />
        </div>
        <div className={styles.nav}>
            <a href="#features" className={styles.navLink}>Features</a>
            <a href="#how-it-works" className={styles.navLink}>How it works</a>
            <a href="#github" className={styles.navLink}>GitHub</a>
            <a href="#contact" className={styles.navBtn}>Get Started</a>
        </div>
    </header>
  )
}

export default Header;