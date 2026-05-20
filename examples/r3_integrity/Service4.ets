
class Service4 {
  private dep4: Service5 = new Service5()

  process(): void {
    this.validate()
    this.dep4.handle()
  }

  private validate(): boolean {
    return true
  }
}
