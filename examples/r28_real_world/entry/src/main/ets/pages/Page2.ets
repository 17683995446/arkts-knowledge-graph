
@Entry
@Component
struct Page2 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 2'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
