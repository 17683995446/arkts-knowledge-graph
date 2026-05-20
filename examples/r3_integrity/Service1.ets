
class Service1 {
  private dep1: Service2 = new Service2()

  process(): void {
    this.validate()
    this.dep1.handle()
  }

  private validate(): boolean {
    return true
  }
}
