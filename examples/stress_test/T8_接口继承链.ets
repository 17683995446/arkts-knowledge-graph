
interface BaseInterface {
  method1(): void
}

interface ExtendedInterface extends BaseInterface {
  method2(): void
}

class BaseImpl implements BaseInterface {
  method1(): void {
    console.info('base method1')
  }
}

class ExtendedImpl extends BaseImpl implements ExtendedInterface {
  method2(): void {
    this.method1()
    console.info('extended method2')
  }
}
