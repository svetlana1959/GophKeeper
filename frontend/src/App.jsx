import { Route, Routes } from 'react-router-dom'
import './App.css'
import Landing from './pages/Landing'
import Registration from './pages/Registration'
import Authorization from './pages/Authorization'
import Logout from './pages/Logout'
import MainPage from './pages/MainPage'

function App() {
  return (
    <Routes>
      <Route path='/' element={<Landing />} />
      <Route path='/register' element={<Registration />} />
      <Route path='/auth' element={<Authorization />} />
      <Route path='/logout' element={<Logout />} />
      <Route path='/dashboard' element={<MainPage linkPage="dashboard" />} />
      <Route path='*' element={<Landing />} />
    </Routes>
  )
}

export default App
