
@Entry
@Component
struct Page16 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 16'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
