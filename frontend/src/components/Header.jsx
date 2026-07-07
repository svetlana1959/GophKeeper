import { Link } from 'react-router-dom'
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
            <a href="#howItWorks" className={styles.navLink}>How it works</a>
            <Link to="/login" className={styles.navLink}>Log in</Link>
            <Link to="/register" className={styles.navBtn}>Get Started</Link>
        </div>
    </header>
  )
}

export default Header; 