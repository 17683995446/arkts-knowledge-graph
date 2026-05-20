
class Service2 {
  private dep2: Service3 = new Service3()

  process(): void {
    this.validate()
    this.dep2.handle()
  }

  private validate(): boolean {
    return true
  }
}
