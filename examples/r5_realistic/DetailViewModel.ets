
import { BaseViewModel } from './BaseViewModel'

export class DetailViewModel extends BaseViewModel {
  private detail: string = ''

  loadDetail(id: string): void {
    this.showLoading()
    this.fetchDetail(id)
  }

  private fetchDetail(id: string): void {
    this.detail = 'item_' + id
    this.hideLoading()
  }
}
