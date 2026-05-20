
class DataHolder0 {
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
struct MixedView0 {
  @State holder: DataHolder0 = new DataHolder0()

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
