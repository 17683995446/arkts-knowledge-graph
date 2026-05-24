/**
 * 深度嵌套结构测试文件
 */

export class Outer14 {
    middle: Middle14 = new Middle14();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle14 {
    inner: Inner14 = new Inner14();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner14 {
    deeplyNested: DeeplyNested14 = new DeeplyNested14();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested14 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
