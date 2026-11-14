import { NuqsAdapter } from 'nuqs/adapters/react-router/v8'
import { BrowserRouter, Route, Routes } from 'react-router'
import { ROUTES } from '../constants/routes'
import { DashboardPage } from '../pages/dashboard/DashboardPage'
import { LoginPage } from '../pages/login/LoginPage'
import { PatientFilePage } from '../pages/patient-file/PatientFilePage'
import { AuthenticatedLayout } from '../shared/components/AuthenticatedLayout'
import { RedirectIfAuthenticated } from '../shared/components/RedirectIfAuthenticated'
import { RequireAuth } from '../shared/components/RequireAuth'

export function App() {
  return (
    <BrowserRouter>
      <NuqsAdapter>
        <Routes>
          <Route element={<RedirectIfAuthenticated />}>
            <Route path={ROUTES.login} element={<LoginPage />} />
          </Route>
          <Route element={<RequireAuth />}>
            <Route element={<AuthenticatedLayout />}>
              <Route path={ROUTES.dashboard} element={<DashboardPage />} />
              <Route path={ROUTES.fiche} element={<PatientFilePage />} />
            </Route>
          </Route>
        </Routes>
      </NuqsAdapter>
    </BrowserRouter>
  )
}
