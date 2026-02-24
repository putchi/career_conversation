import {defineCliConfig} from 'sanity/cli'

export default defineCliConfig({
  api: {
    projectId: 'tpg3gf74',
    dataset: 'production',
  },
  studioHost: 'alexr-career-conversation',
  deployment: {
    /**
     * Enable auto-updates for studios.
     * Learn more at https://www.sanity.io/docs/studio/latest-version-of-sanity#k47faf43faf56
     */
    autoUpdates: true,
    appId: 'p3waigxb2xe4l7zygz24ehsy',
  },
})
