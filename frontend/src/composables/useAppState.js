import { inject } from 'vue'

export function useAppState() {
  return inject('appState')
}