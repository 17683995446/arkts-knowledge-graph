
class Service7 {
  private dep7: Service8 = new Service8()

  process(): void {
    this.validate()
    this.dep7.handle()
  }

  private validate(): boolean {
    return true
  }
}
