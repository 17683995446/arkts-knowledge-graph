
@Entry
@Component
struct Page7 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 7'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
