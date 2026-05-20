
@Entry
@Component
struct Page28 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 28'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
