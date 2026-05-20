
// class FakeClass { this is a fake class in comment }
/* 
class AnotherFake {
  method(): void {}
}
*/
class RealClass {
  // this.fakeMethod(): void {}
  realMethod(): void {
    // this.fakeCall()
    this.actualCall()
  }
  private actualCall(): void {}
}
