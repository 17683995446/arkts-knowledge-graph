
@Entry
@Component
struct Page10 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 10'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
