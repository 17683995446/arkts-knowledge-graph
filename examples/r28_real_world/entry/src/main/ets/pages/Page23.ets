
@Entry
@Component
struct Page23 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 23'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
