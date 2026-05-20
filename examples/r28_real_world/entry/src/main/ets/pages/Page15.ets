
@Entry
@Component
struct Page15 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 15'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
