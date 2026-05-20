
@Entry
@Component
struct Page21 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 21'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
