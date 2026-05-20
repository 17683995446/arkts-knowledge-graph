
@Entry
@Component
@CustomDialog
struct DecoratedDialog {
  @State private visible: boolean = false
  @Link private data: string = ''
  @Provide('theme') theme: string = 'dark'
  
  aboutToAppear(): void {
    this.init()
  }
  
  build() {
    Column() {
      Text(this.data)
    }
  }
  
  private init(): void {
    this.visible = true
  }
}
