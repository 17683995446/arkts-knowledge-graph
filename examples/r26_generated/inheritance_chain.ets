
class Base {
  protected id: string = ''
  
  init(): void {
    this.id = Date.now().toString()
  }
  
  protected validate(): boolean {
    return this.id.length > 0
  }
}

class Middleware extends Base {
  protected next: Middleware | null = null
  
  setNext(next: Middleware): Middleware {
    this.next = next
    return next
  }
  
  handle(): void {
    if (this.validate()) {
      this.process()
      if (this.next) {
        this.next.handle()
      }
    }
  }
  
  protected process(): void {}
}

class AuthMiddleware extends Middleware {
  private token: string = ''
  
  setToken(t: string): void {
    this.token = t
  }
  
  protected process(): void {
    console.info(`Auth with ${this.token}`)
  }
}

class LogMiddleware extends Middleware {
  protected process(): void {
    console.info(`Logging for ${this.id}`)
  }
}

class CacheMiddleware extends Middleware {
  private cache: Map<string, any> = new Map()
  
  protected process(): void {
    console.info(`Caching for ${this.id}`)
  }
  
  clear(): void {
    this.cache.clear()
  }
}
