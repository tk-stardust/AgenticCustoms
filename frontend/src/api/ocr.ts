import client from './client'

export interface OCRResponse {
  name: string
  material: string
  function: string
  usage: string
  description: string
}

export async function ocrImage(base64: string, imageType: string): Promise<OCRResponse> {
  const { data } = await client.post<OCRResponse>('/ocr', {
    image_base64: base64,
    image_type: imageType,
  })
  return data
}
