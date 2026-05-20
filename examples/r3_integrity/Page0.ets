
@Entry
@Component
struct Page0 {
  @State data: string = ''

  aboutToAppear(): void {
    this.loadData()
  }

  build() {
    Column() {
      Text(this.data)
        .onClick(() => this.handleClick())
      ChildComp1()
    }
  }

  private handleClick(): void {
    console.info('clicked')
  }

  private loadData(): void {
    this.data = 'loaded'
  }
}
