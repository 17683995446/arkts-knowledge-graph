
import { ServiceA } from './ServiceA'

export class ServiceB {
  private a: ServiceA | null = null
  
  setA(a: ServiceA): void {
    this.a = a
  }
  
  process(): void {
    if (this.a) {
      this.a.helper()
    }
  }
  
  helper(): void {
    console.info('ServiceB helper')
  }
}
