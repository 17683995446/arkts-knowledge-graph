
@Entry
@Component
struct Page24 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 24'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
