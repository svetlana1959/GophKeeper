import { Route, Routes } from 'react-router-dom'
import './App.css'
import Landing from './pages/Landing'
import Registration from './pages/Registration'
import Authorization from './pages/Authorization'

function App() {
  return (
    <Routes>
      <Route path='/' element={<Landing />}/>
      <Route path='/register' element={<Registration />}/>
      <Route path='/auth' element={<Authorization />}/>
    </Routes>
  )
}

export default App
