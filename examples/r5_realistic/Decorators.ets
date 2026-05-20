
@Component
struct DecoratorDemo {
  @State count: number = 0
  @Prop title: string = ''
  @Watch('count') onCountChange(): void {
    console.info('count changed')
  }

  aboutToAppear(): void {
    this.loadData()
  }

  build() {
    Column() {
      Text(this.title)
      this.TitleBuilder()
      Button('Add')
        .onClick(() => this.increment())
    }
  }

  @Builder TitleBuilder() {
    Text('Title: ' + this.title)
      .fontSize(20)
  }

  private increment(): void {
    this.count++
  }

  private loadData(): void {
    this.count = 10
  }
}

@Extend(Text) function boldStyle() {
  .fontWeight(FontWeight.Bold)
}
