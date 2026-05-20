
class ValidClass1 {
  method1(): void {}
}

// 语法错误：未闭合的字符串
class InvalidClass {
  private str: string = 'unclosed string
  
  method(): void {}
}

class ValidClass2 {
  method2(): void {}
}

// 语法错误：未闭合的大括号
class AnotherInvalid {
  method(): void {
    if (true) {
      console.info('test'
    }
}

class ValidClass3 {
  method3(): void {}
}
