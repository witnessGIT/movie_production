import type { AppSettings, Asset, Capability, Job, Project } from './types'

const json = async <T>(input: RequestInfo, init?: RequestInit): Promise<T> => {
  const response = await fetch(input, init)
  if (!response.ok) throw new Error(await response.text())
  return response.json()
}

export const api = {
  capabilities: () => json<Capability[]>('/api/capabilities'),
  settings: () => json<AppSettings>('/api/settings'),
  saveSettings: (settings: AppSettings) => json<AppSettings>('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings) }),
  openGptProfile: (id: string) => json<{ok:boolean; message:string}>(`/api/gpt-profiles/${id}/open`, { method: 'POST' }),
  projects: () => json<Project[]>('/api/projects'),
  createProject: (title: string, source_text: string) => json<Project>('/api/projects', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, source_text }) }),
  updateProject: (id: string, title: string, source_text: string) => json<Project>(`/api/projects/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, source_text }) }),
  assets: (id: string) => json<Asset[]>(`/api/projects/${id}/assets`),
  addUrl: (id: string, url: string, label = '', source_type = 'reference') => json<Asset>(`/api/projects/${id}/assets/url`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url, label, source_type }) }),
  addText: (id: string, label: string, text: string) => json<Asset>(`/api/projects/${id}/assets/text`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ label, text }) }),
  upload: async (id: string, file: File) => { const body = new FormData(); body.append('file', file); return json<Asset>(`/api/projects/${id}/assets/upload`, { method: 'POST', body }) },
  startJob: (id: string) => json<Job>(`/api/projects/${id}/jobs`, { method: 'POST' }),
  jobs: (id: string) => json<Job[]>(`/api/projects/${id}/jobs`),
  artifact: (projectId: string, jobId: string, stageId: string) => json<any>(`/api/projects/${projectId}/jobs/${jobId}/artifacts/${stageId}`),
  outputUrl: (projectId: string, jobId: string) => `/api/projects/${projectId}/jobs/${jobId}/output`,
}

export function jobSocket(jobId: string) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return new WebSocket(`${proto}://${location.host}/ws/jobs/${jobId}`)
}
