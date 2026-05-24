/**
 * 深度嵌套结构测试文件
 */

export class Outer17 {
    middle: Middle17 = new Middle17();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle17 {
    inner: Inner17 = new Inner17();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner17 {
    deeplyNested: DeeplyNested17 = new DeeplyNested17();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested17 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
