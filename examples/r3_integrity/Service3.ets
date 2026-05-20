
class Service3 {
  private dep3: Service4 = new Service4()

  process(): void {
    this.validate()
    this.dep3.handle()
  }

  private validate(): boolean {
    return true
  }
}
