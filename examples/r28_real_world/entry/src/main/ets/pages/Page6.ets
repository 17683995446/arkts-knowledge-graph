
@Entry
@Component
struct Page6 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 6'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
