
@Entry
@Component
struct Page14 {
  @State private data: string = ''
  
  aboutToAppear(): void {
    this.loadData()
  }
  
  private loadData(): void {
    this.data = 'Page 14'
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
}
