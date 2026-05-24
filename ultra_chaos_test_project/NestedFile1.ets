/**
 * 深度嵌套结构测试文件
 */

export class Outer1 {
    middle: Middle1 = new Middle1();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle1 {
    inner: Inner1 = new Inner1();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner1 {
    deeplyNested: DeeplyNested1 = new DeeplyNested1();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested1 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
