
@Entry
@Component
struct Page9 {
  @State data: string = ''

  aboutToAppear(): void {
    this.loadData()
  }

  build() {
    Column() {
      Text(this.data)
        .onClick(() => this.handleClick())

    }
  }

  private handleClick(): void {
    console.info('clicked')
  }

  private loadData(): void {
    this.data = 'loaded'
  }
}
