
// 空类
class EmptyClass {}

// 只有属性的类
class PropertiesOnly {
  public name: string = ''
  private _id: number = 0
  protected count: number = 0
  readonly constant: string = 'CONST'
}

// 只有静态方法的类
class StaticOnly {
  static method1(): void {}
  static method2(): string { return '' }
  static method3(n: number): number { return n * 2 }
}

// 只有私有方法的类
class PrivateOnly {
  private helper1(): void {}
  private helper2(): string { return '' }
}

// 极长方法名
class LongNames {
  thisIsAVeryVeryVeryLongMethodNameThatExceedsNormalLength(): void {}
  
  anotherExtremelyLongMethodNameThatShouldStillBeParsedCorrectly(): string {
    return 'test'
  }
}

// 特殊字符方法名（$和_）
class SpecialChars {
  $dollarMethod(): void {}
  _underscoreMethod(): void {}
  $__mixed$Method(): void {}
}

// 空方法体
class EmptyMethods {
  method1(): void {}
  method2(): string { return '' }
  method3(): number { return 0 }
}

// 嵌套类（TypeScript不支持，但测试解析器健壮性）
class OuterClass {
  outerMethod(): void {}
  
  // 这在ArkTS中是无效的，但解析器不应崩溃
}

// 多重继承模拟
class MultiImplement implements I1, I2, I3 {
  method1(): void {}
  method2(): void {}
  method3(): void {}
}

interface I1 { method1(): void }
interface I2 { method2(): void }
interface I3 { method3(): void }

// 泛型类
class GenericClass<T, U> {
  private data: T | null = null
  private mapper: ((t: T) => U) | null = null
  
  set(value: T): void {
    this.data = value
  }
  
  map(mapper: (t: T) => U): U | null {
    return this.data ? mapper(this.data) : null
  }
}

// 抽象类模拟
class AbstractLikeClass {
  protected abstractMethod(): void {
    throw new Error('Not implemented')
  }
  
  concreteMethod(): void {
    this.abstractMethod()
  }
}
