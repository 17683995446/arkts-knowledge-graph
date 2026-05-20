
@Entry
@Component
struct Page4 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 4'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
