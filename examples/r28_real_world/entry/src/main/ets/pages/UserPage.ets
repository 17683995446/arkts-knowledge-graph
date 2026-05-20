
import { UserViewModel } from '../viewmodels/UserViewModel'

@Entry
@Component
struct UserPage {
  @State private viewModel: UserViewModel = new UserViewModel()
  @State private userName: string = ''
  @State private userEmail: string = ''
  @State private isLoading: boolean = false
  
  aboutToAppear(): void {
    this.loadUserData()
  }
  
  private async loadUserData(): Promise<void> {
    this.isLoading = true
    await this.viewModel.loadUser('123')
    this.userName = this.viewModel.getUserName()
    this.userEmail = this.viewModel.getUserEmail()
    this.isLoading = false
  }
  
  build() {
    Column() {
      if (this.isLoading) {
        Text('Loading...')
      } else {
        Text(this.userName)
        Text(this.userEmail)
        Button('Refresh')
          .onClick(() => this.loadUserData())
      }
    }
  }
}
