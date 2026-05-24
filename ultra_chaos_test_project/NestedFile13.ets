/**
 * 深度嵌套结构测试文件
 */

export class Outer13 {
    middle: Middle13 = new Middle13();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle13 {
    inner: Inner13 = new Inner13();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner13 {
    deeplyNested: DeeplyNested13 = new DeeplyNested13();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested13 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
