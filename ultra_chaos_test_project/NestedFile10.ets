/**
 * 深度嵌套结构测试文件
 */

export class Outer10 {
    middle: Middle10 = new Middle10();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle10 {
    inner: Inner10 = new Inner10();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner10 {
    deeplyNested: DeeplyNested10 = new DeeplyNested10();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested10 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
