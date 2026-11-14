import { NuqsAdapter } from 'nuqs/adapters/react-router/v8'
import { BrowserRouter, Route, Routes } from 'react-router'
import { ROUTES } from '../constants/routes'
import { DashboardPage } from '../pages/dashboard/DashboardPage'
import { LoginPage } from '../pages/login/LoginPage'
import { PatientFilePage } from '../pages/patient-file/PatientFilePage'

export function App() {
  return (
    <BrowserRouter>
      <NuqsAdapter>
        <Routes>
          <Route path={ROUTES.login} element={<LoginPage />} />
          <Route path={ROUTES.dashboard} element={<DashboardPage />} />
          <Route path={ROUTES.fiche} element={<PatientFilePage />} />
        </Routes>
      </NuqsAdapter>
    </BrowserRouter>
  )
}
