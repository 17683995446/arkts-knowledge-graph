
import { ServiceB } from './ServiceB'

export class ServiceA {
  private b: ServiceB | null = null
  
  setB(b: ServiceB): void {
    this.b = b
  }
  
  process(): void {
    if (this.b) {
      this.b.helper()
    }
  }
  
  helper(): void {
    console.info('ServiceA helper')
  }
}
