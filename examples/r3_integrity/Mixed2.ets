
class DataHolder2 {
  value: string = ''

  get(): string {
    return this.value
  }

  set(v: string): void {
    this.value = v
    this.validate()
  }

  private validate(): boolean {
    return this.value.length > 0
  }
}

@Component
struct MixedView2 {
  @State holder: DataHolder2 = new DataHolder2()

  build() {
    Row() {
      Text(this.holder.get())
        .onClick(() => this.refresh())
    }
  }

  private refresh(): void {
    console.info('refreshed')
  }
}
