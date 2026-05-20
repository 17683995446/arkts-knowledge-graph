
import { RouterA } from './RouterA'
import { RouterB } from './RouterB'

export class RouterC {
  private routerA: RouterA = new RouterA()
  private routerB: RouterB = new RouterB()

  navigateAll(): void {
    this.routerA.navigateToA()
    this.routerB.navigateToB()
  }
}
