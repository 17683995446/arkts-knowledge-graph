
@Entry
@Component
struct Page1 {
  @State data: string = ''

  aboutToAppear(): void {
    this.loadData()
  }

  build() {
    Column() {
      Text(this.data)
        .onClick(() => this.handleClick())
      ChildComp2()
    }
  }

  private handleClick(): void {
    console.info('clicked')
  }

  private loadData(): void {
    this.data = 'loaded'
  }
}
