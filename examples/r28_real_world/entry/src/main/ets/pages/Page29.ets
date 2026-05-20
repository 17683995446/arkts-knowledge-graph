
@Entry
@Component
struct Page29 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 29'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
