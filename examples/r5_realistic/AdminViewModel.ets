
import { UserViewModel } from './UserViewModel'

export class AdminViewModel extends UserViewModel {
  private role: string = 'admin'

  loadAdmin(): void {
    this.showLoading()
    this.loadUser()
    this.checkPermission()
  }

  private checkPermission(): void {
    this.hideLoading()
  }
}
