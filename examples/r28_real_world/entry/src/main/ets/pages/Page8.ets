
@Entry
@Component
struct Page8 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 8'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
