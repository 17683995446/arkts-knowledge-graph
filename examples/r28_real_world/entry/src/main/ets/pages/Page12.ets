
@Entry
@Component
struct Page12 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 12'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
