/**
 * 深度嵌套结构测试文件
 */

export class Outer5 {
    middle: Middle5 = new Middle5();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle5 {
    inner: Inner5 = new Inner5();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner5 {
    deeplyNested: DeeplyNested5 = new DeeplyNested5();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested5 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
