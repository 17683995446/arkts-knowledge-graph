
@Entry
@Component
struct Page3 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 3'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
