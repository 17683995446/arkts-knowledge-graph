
@Entry
@Component
struct Page1 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 1'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
