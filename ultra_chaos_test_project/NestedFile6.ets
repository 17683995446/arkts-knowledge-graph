/**
 * 深度嵌套结构测试文件
 */

export class Outer6 {
    middle: Middle6 = new Middle6();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle6 {
    inner: Inner6 = new Inner6();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner6 {
    deeplyNested: DeeplyNested6 = new DeeplyNested6();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested6 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
