
class Service8 {
  private dep8: Service9 = new Service9()

  process(): void {
    this.validate()
    this.dep8.handle()
  }

  private validate(): boolean {
    return true
  }
}
