
class Service6 {
  private dep6: Service7 = new Service7()

  process(): void {
    this.validate()
    this.dep6.handle()
  }

  private validate(): boolean {
    return true
  }
}
