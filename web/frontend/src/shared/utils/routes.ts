import { FICHE_ID_PARAM, ROUTES } from '../../constants/routes'

export function buildFichePath(id: string): string {
  return ROUTES.fiche.replace(`:${FICHE_ID_PARAM}`, encodeURIComponent(id))
}
