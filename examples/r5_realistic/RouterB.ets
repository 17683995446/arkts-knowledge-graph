
import { RouterA } from './RouterA'

export class RouterB {
  private routerA: RouterA = new RouterA()

  navigateToB(): void {
    this.routerA.handleBack()
  }

  handleBack(): void {
    console.info('back from B')
  }
}
