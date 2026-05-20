
@Entry
@Component
struct Page25 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 25'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
