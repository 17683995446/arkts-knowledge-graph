
@Entry
@Component
struct Page27 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 27'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
