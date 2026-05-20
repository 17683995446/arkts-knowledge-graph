
import { ListViewModel } from './ListViewModel'

export class UserViewModel extends ListViewModel {
  private userName: string = ''

  loadUser(): void {
    this.showLoading()
    this.loadItems()
  }

  private fetchUserData(): void {
    this.userName = 'test'
    this.hideLoading()
  }

  private newUserMethod(): void {
    console.info('new user method')
  }
}
