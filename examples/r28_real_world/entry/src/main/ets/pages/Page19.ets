
@Entry
@Component
struct Page19 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 19'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
