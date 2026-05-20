
@Entry
@Component
struct Page20 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 20'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
