
class DataHolder4 {
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
struct MixedView4 {
  @State holder: DataHolder4 = new DataHolder4()

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
