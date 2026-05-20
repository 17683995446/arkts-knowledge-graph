
@Entry
@Component
struct Page9 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 9'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
