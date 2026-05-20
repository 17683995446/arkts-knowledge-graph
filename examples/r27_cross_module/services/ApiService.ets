
import HttpClient, { HttpResponse } from '../utils/HttpClient'

export class ApiService {
  private client: HttpClient = new HttpClient()
  
  async fetchData(): Promise<HttpResponse> {
    return this.client.get('/data')
  }
  
  async sendData(data: any): Promise<HttpResponse> {
    return this.client.post('/data', data)
  }
}
