import { defineConfig } from 'sanity'
import { structureTool } from 'sanity/structure'
import { schemaTypes } from './schemas'

// WARNING: This config targets the live Sanity project. Running `npm run deploy`
// will deploy Studio to that project. Use your own project ID if forking this repo.
export default defineConfig({
  name: 'default',
  title: 'Career Conversation',
  projectId: 'tpg3gf74',
  dataset: 'production',
  plugins: [structureTool()],
  schema: { types: schemaTypes },
})
