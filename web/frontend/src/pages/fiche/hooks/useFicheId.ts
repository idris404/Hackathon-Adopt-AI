import { useParams } from 'react-router'
import { FICHE_ID_PARAM } from '../../../constants/routes'

export function useFicheId(): string | undefined {
  return useParams()[FICHE_ID_PARAM]
}
