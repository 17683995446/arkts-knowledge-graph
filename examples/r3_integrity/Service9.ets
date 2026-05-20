
class Service9 {
  private dep9: Service0 = new Service0()

  process(): void {
    this.validate()
    this.dep9.handle()
  }

  private validate(): boolean {
    return true
  }
}
