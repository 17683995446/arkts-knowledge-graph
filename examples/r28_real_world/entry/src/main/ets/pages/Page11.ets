
@Entry
@Component
struct Page11 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 11'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
