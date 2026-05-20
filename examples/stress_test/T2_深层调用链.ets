
class ServiceA {
  private serviceB: ServiceB = new ServiceB()

  doWork(): void {
    this.serviceB.process()
    this.validate()
  }

  private validate(): boolean {
    return true
  }
}

class ServiceB {
  private serviceC: ServiceC = new ServiceC()

  process(): void {
    this.serviceC.execute()
    this.log()
  }

  private log(): void {
    console.info('processing')
  }
}

class ServiceC {
  private serviceD: ServiceD = new ServiceD()

  execute(): void {
    this.serviceD.run()
  }
}

class ServiceD {
  private serviceE: ServiceE = new ServiceE()

  run(): void {
    this.serviceE.finalize()
    this.cleanup()
  }

  private cleanup(): void {
    console.info('cleaned up')
  }
}

class ServiceE {
  finalize(): void {
    console.info('done')
  }
}
