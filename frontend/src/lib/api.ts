import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export default api

// typed helpers
export async function uploadPdf(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await api.post('/documents/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  return data
}
export async function getStats() {
  const { data } = await api.get('/stats')
  return data
}
export async function listDocs(params?: any) {
  const { data } = await api.get('/documents/', { params })
  return data
}
