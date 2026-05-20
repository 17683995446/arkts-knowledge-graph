
class ChainDemo {
  private builder: RequestBuilder = new RequestBuilder()

  execute(): void {
    this.builder.setUrl('https://api.example.com')
      .setMethod('GET')
      .setTimeout(5000)
      .send()
  }
}

class RequestBuilder {
  private url: string = ''
  private method: string = 'GET'
  private timeout: number = 3000

  setUrl(url: string): RequestBuilder {
    this.url = url
    return this
  }

  setMethod(method: string): RequestBuilder {
    this.method = method
    return this
  }

  setTimeout(timeout: number): RequestBuilder {
    this.timeout = timeout
    return this
  }

  send(): void {
    console.info(this.method + ' ' + this.url)
  }
}
