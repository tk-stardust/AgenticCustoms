import client from './client'
import type { Commodity, PipelineFullResponse } from '@/types'

export async function runFullPipeline(
  commodity: Commodity,
  targetCountry: string = 'US',
  signal?: AbortSignal,
): Promise<PipelineFullResponse> {
  const { data } = await client.post<PipelineFullResponse>(
    `/pipeline/full?target_country=${targetCountry}`,
    commodity,
    { timeout: 300000, signal },
  )
  return data
}

export type ProgressCallback = (event: string, data: Record<string, unknown>) => void

export async function runPipelineSSE(
  commodity: Commodity,
  targetCountry: string,
  onProgress: ProgressCallback,
  signal?: AbortSignal,
): Promise<PipelineFullResponse> {
  const resp = await fetch(`/api/pipeline/stream?target_country=${targetCountry}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(commodity),
    signal,
  })

  if (!resp.ok || !resp.body) throw new Error(`SSE 连接失败 (${resp.status})`)

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  return new Promise((resolve, reject) => {
    function pump() {
      reader.read().then(({ done, value }) => {
        if (done) { reject(new Error('SSE 流提前关闭')); return }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''  // 保留不完整的最后一行

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (currentEvent === 'done') {
                reader.cancel()
                resolve(data as unknown as PipelineFullResponse)
              } else {
                onProgress(currentEvent, data)
                currentEvent = ''
              }
            } catch { /* 忽略解析失败的行 */ }
          }
        }
        pump()
      }).catch(reject)
    }
    pump()
  })
}
