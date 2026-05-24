/**
 * 深度嵌套结构测试文件
 */

export class Outer18 {
    middle: Middle18 = new Middle18();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle18 {
    inner: Inner18 = new Inner18();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner18 {
    deeplyNested: DeeplyNested18 = new DeeplyNested18();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested18 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
