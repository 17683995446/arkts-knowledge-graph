/**
 * 深度嵌套结构测试文件
 */

export class Outer9 {
    middle: Middle9 = new Middle9();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle9 {
    inner: Inner9 = new Inner9();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner9 {
    deeplyNested: DeeplyNested9 = new DeeplyNested9();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested9 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
