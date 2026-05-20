
@Entry
@Component
struct Page18 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 18'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
