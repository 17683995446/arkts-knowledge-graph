
@Entry
@Component
struct Page13 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 13'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
