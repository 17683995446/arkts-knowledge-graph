/**
 * 单字符标识符测试
 */

export class A {
    b: string;
    c() {
        return this.b;
    }
}

export class B {
    a: A;
    d() {
        return new A();
    }
}
