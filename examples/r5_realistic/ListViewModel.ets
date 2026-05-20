
import { BaseViewModel } from './BaseViewModel'

export class ListViewModel extends BaseViewModel {
  private items: string[] = []
  private page: number = 1

  loadItems(): void {
    this.showLoading()
    this.fetchData()
  }

  private fetchData(): void {
    this.page++
    this.hideLoading()
  }

  refresh(): void {
    this.page = 1
    this.clearError()
    this.loadItems()
  }

  private newMethod(): void {
    console.info('new method added')
  }
}
