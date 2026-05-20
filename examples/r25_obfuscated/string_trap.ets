
class StringTrap {
  private code: string = """
class FakeClass {
  fakeMethod(): void {
    this.fakeCall()
  }
}
"""
  
  realMethod(): void {
    const fake = 'class AnotherFake { method(): void {} }'
    this.helper()
  }
  
  private helper(): void {}
}
