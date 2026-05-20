
@Entry
@Component
struct Page0 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 0'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
