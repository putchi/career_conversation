export default {
  name: 'profile',
  title: 'Profile',
  type: 'document',
  fields: [
    { name: 'name',        title: 'Name',                  type: 'string' },
    { name: 'title',       title: 'Title',                 type: 'string' },
    { name: 'linkedinUrl', title: 'LinkedIn URL',           type: 'url'    },
    { name: 'websiteUrl',  title: 'Website URL',            type: 'url'    },
    {
      name: 'suggestions',
      title: 'Chat Suggestions',
      type: 'array',
      of: [{ type: 'string' }],
    },
    { name: 'summary',      title: 'Summary',               type: 'text' },
    { name: 'model',        title: 'OpenAI Model',          type: 'string' },
    { name: 'profilePdf',   title: 'Profile PDF',           type: 'file' },
    { name: 'referencePdf', title: 'Reference Letter PDF',  type: 'file' },
  ],
}
