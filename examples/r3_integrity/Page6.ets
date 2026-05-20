
@Entry
@Component
struct Page6 {
  @State data: string = ''

  aboutToAppear(): void {
    this.loadData()
  }

  build() {
    Column() {
      Text(this.data)
        .onClick(() => this.handleClick())
      ChildComp7()
    }
  }

  private handleClick(): void {
    console.info('clicked')
  }

  private loadData(): void {
    this.data = 'loaded'
  }
}
