
class DataHolder3 {
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
struct MixedView3 {
  @State holder: DataHolder3 = new DataHolder3()

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
