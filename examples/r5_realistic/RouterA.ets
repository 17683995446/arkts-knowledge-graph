
import { RouterB } from './RouterB'

export class RouterA {
  private routerB: RouterB = new RouterB()

  navigateToA(): void {
    this.routerB.navigateToB()
  }

  handleBack(): void {
    console.info('back from A')
  }
}
