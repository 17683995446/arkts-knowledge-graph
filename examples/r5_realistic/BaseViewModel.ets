
export class BaseViewModel {
  protected isLoading: boolean = false
  protected errorMessage: string = ''

  showLoading(): void {
    this.isLoading = true
  }

  hideLoading(): void {
    this.isLoading = false
  }

  setError(msg: string): void {
    this.errorMessage = msg
    this.hideLoading()
  }

  clearError(): void {
    this.errorMessage = ''
  }
}
