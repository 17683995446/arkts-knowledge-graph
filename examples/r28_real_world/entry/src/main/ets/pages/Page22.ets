
@Entry
@Component
struct Page22 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 22'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
