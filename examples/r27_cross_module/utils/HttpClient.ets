
export interface HttpResponse {
  status: number
  data: any
}

export class HttpClient {
  private baseUrl: string = ''
  
  setBaseUrl(url: string): void {
    this.baseUrl = url
  }
  
  async get(path: string): Promise<HttpResponse> {
    return { status: 200, data: null }
  }
  
  async post(path: string, body: any): Promise<HttpResponse> {
    return { status: 201, data: body }
  }
}

export default HttpClient
