
class HttpRequest {
  private _method: string = 'GET'
  private _url: string = ''
  private _headers: Map<string, string> = new Map()
  private _body: string = ''
  private _timeout: number = 30000
  
  static builder(): HttpRequestBuilder {
    return new HttpRequestBuilder()
  }
  
  send(): void {
    console.info(`Sending ${this._method} to ${this._url}`)
  }
}

class HttpRequestBuilder {
  private request: HttpRequest = new HttpRequest()
  
  method(m: string): HttpRequestBuilder {
    this.request._method = m
    return this
  }
  
  url(u: string): HttpRequestBuilder {
    this.request._url = u
    return this
  }
  
  header(key: string, value: string): HttpRequestBuilder {
    this.request._headers.set(key, value)
    return this
  }
  
  body(b: string): HttpRequestBuilder {
    this.request._body = b
    return this
  }
  
  timeout(t: number): HttpRequestBuilder {
    this.request._timeout = t
    return this
  }
  
  build(): HttpRequest {
    return this.request
  }
}
