
class Service0 {
  private dep0: Service1 = new Service1()

  process(): void {
    this.validate()
    this.dep0.handle()
    this.newMethod()
  }

  private validate(): boolean {
    return true
  }

  private newMethod(): void {
    console.info('new method')
  }
}
